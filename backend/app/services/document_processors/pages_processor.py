"""
Apple Pages (.pages) 文件處理器
支援 ZIP 格式的 .pages 檔案以及已解壓的 .pages 目錄

策略：
1. IWA 檔案使用 Snappy 壓縮（4-byte 分幀: type + 3-byte LE length）
2. 解壓後掃描 protobuf wire-type-2 欄位，提取 UTF-8 字串
3. 過濾出有意義的文字內容（CJK / 長英文）
"""
import os
import re
import zipfile
from io import BytesIO
from typing import List, Optional

from app.services.document_processors.base import (
    BaseDocumentProcessor,
    ProcessedDocument,
    PageText,
)

# 嘗試載入 snappy（可選依賴）
try:
    import snappy

    _HAS_SNAPPY = True
except ImportError:
    _HAS_SNAPPY = False


# ========== IWA 解壓 ==========


def _read_varint(data: bytes, pos: int) -> tuple[Optional[int], int]:
    """讀取 protobuf varint，回傳 (value, new_pos)。"""
    result = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if (b & 0x80) == 0:
            return result, pos
        shift += 7
        if shift > 63:
            return None, pos
    return None, pos


def _decompress_iwa(raw: bytes) -> bytes:
    """解壓 IWA 的 Snappy 分幀格式。

    IWA 使用 Snappy framing：每個 chunk 為 [type(1)] [3-byte LE length] [data]
    type=0x00: Snappy 壓縮資料
    type=0x01: 未壓縮資料
    type=0xff: Stream identifier（忽略）
    """
    if not _HAS_SNAPPY:
        return raw

    chunks: list[bytes] = []
    pos = 0

    while pos + 4 <= len(raw):
        chunk_type = raw[pos]
        chunk_len = raw[pos + 1] | (raw[pos + 2] << 8) | (raw[pos + 3] << 16)
        pos += 4

        if chunk_len <= 0 or pos + chunk_len > len(raw):
            break

        chunk_data = raw[pos : pos + chunk_len]
        pos += chunk_len

        if chunk_type == 0x00:
            # Snappy compressed chunk
            try:
                chunks.append(snappy.decompress(chunk_data))
            except Exception:
                # 壓縮失敗時使用原始資料
                chunks.append(chunk_data)
        elif chunk_type == 0x01:
            # Uncompressed chunk
            chunks.append(chunk_data)
        elif chunk_type == 0xFF:
            # Stream identifier, skip
            pass
        else:
            # Unknown chunk type, include raw data
            chunks.append(chunk_data)

    if not chunks:
        return raw

    return b"".join(chunks)


# ========== Protobuf 字串掃描 ==========


def _scan_protobuf_strings(data: bytes, min_len: int = 10) -> list[str]:
    """掃描二進位資料中的 protobuf wire-type-2 欄位，提取 UTF-8 字串。

    此方法不需要知道完整的 protobuf schema，
    而是掃描所有可能的 tag+length 組合來找到字串欄位。
    """
    strings: list[str] = []
    i = 0

    while i < len(data) - 2:
        # 嘗試讀取 protobuf tag
        tag, tag_end = _read_varint(data, i)
        if tag is None or tag_end == i:
            i += 1
            continue

        wire_type = tag & 0x07
        field_num = tag >> 3

        # 只關心 wire type 2 (length-delimited)
        if wire_type != 2 or field_num == 0 or field_num > 10000:
            i += 1
            continue

        # 讀取長度
        length, data_start = _read_varint(data, tag_end)
        if length is None or length < min_len or length > 500_000:
            i += 1
            continue
        if data_start + length > len(data):
            i += 1
            continue

        field_data = data[data_start : data_start + length]

        # 嘗試解碼為 UTF-8
        try:
            text = field_data.decode("utf-8")
            if "\x00" in text:
                i += 1
                continue
        except (UnicodeDecodeError, ValueError):
            i += 1
            continue

        # 有效 UTF-8 字串！檢查是否有意義
        if _has_meaningful_content(text):
            strings.append(text)
            # 跳過已處理的資料
            i = data_start + length
        else:
            i += 1

    return strings


_LOCALE_PATTERN = re.compile(
    r"(?:gorian|latn)"
    r"|(?:\d+月.*){5,}"    # 5+ month references = locale data
    r"|^[A-Z]{3}\x12"     # currency code protobuf fragments
)


def _has_meaningful_content(text: str) -> bool:
    """字串是否包含實質內容（CJK / 有意義的拉丁文 / emoji）。"""
    # 排除 locale / calendar metadata
    if _LOCALE_PATTERN.search(text):
        return False
    # 含有 2+ 個 CJK 字元
    if re.search(r"[\u4e00-\u9fff\u3400-\u4dbf]{2,}", text):
        return True
    # 較長且含有英文單詞
    if len(text) > 30 and re.search(r"[a-zA-Z]{4,}", text):
        return True
    # 含有 emoji
    if re.search(r"[\U0001f300-\U0001f9ff]", text):
        return True
    return False


# ========== Brute-force UTF-8 掃描 (fallback) ==========


def _find_utf8_runs(data: bytes, min_len: int = 6) -> list[str]:
    """從二進位資料中提取連續有效 UTF-8 文字片段（無 snappy 時的備用方案）。"""
    runs: list[str] = []
    i = 0
    while i < len(data):
        run_start = i
        chars: list[str] = []
        while i < len(data):
            b = data[i]
            if b < 0x80:
                if b >= 0x20 or b in (0x0A, 0x0D):
                    chars.append(chr(b))
                    i += 1
                else:
                    break
            elif b < 0xC0:
                break
            elif b < 0xE0:
                if i + 1 < len(data) and (data[i + 1] & 0xC0) == 0x80:
                    try:
                        chars.append(data[i : i + 2].decode("utf-8"))
                        i += 2
                    except Exception:
                        break
                else:
                    break
            elif b < 0xF0:
                if (
                    i + 2 < len(data)
                    and (data[i + 1] & 0xC0) == 0x80
                    and (data[i + 2] & 0xC0) == 0x80
                ):
                    try:
                        chars.append(data[i : i + 3].decode("utf-8"))
                        i += 3
                    except Exception:
                        break
                else:
                    break
            elif b < 0xF8:
                if i + 3 < len(data) and all(
                    (data[i + j] & 0xC0) == 0x80 for j in range(1, 4)
                ):
                    try:
                        chars.append(data[i : i + 4].decode("utf-8"))
                        i += 4
                    except Exception:
                        break
                else:
                    break
            else:
                break

        if chars:
            text = "".join(chars).strip()
            if len(text) >= min_len and _has_meaningful_content(text):
                runs.append(text)

        if i == run_start:
            i += 1

    return runs


# ========== 核心提取邏輯 ==========


def _extract_text_from_iwa_data(raw: bytes) -> list[str]:
    """從單個 IWA 檔案提取文字。

    優先使用 Snappy 解壓 + protobuf 掃描（品質高），
    若 snappy 不可用則退回 brute-force UTF-8 掃描。
    """
    if _HAS_SNAPPY:
        decompressed = _decompress_iwa(raw)
        strings = _scan_protobuf_strings(decompressed, min_len=10)
        if strings:
            return strings

    # Fallback: brute-force UTF-8 掃描
    return _find_utf8_runs(raw, min_len=6)


def _extract_text_from_iwa_files(iwa_contents: dict[str, bytes]) -> str:
    """從所有 IWA 檔案中提取並合併文字。"""
    # 優先處理 Document.iwa（主要文字內容）
    target_files: list[str] = []
    for key in sorted(iwa_contents.keys()):
        if "Document.iwa" in key:
            target_files.insert(0, key)
        elif "Tables/" in key or "DataList" in key:
            target_files.append(key)

    all_strings: list[str] = []
    seen: set[str] = set()

    for key in target_files:
        raw = iwa_contents[key]
        strings = _extract_text_from_iwa_data(raw)
        for s in strings:
            if s not in seen:
                seen.add(s)
                all_strings.append(s)

    if not all_strings:
        return ""

    # 合併所有提取的字串，清理特殊字元
    text = "\n\n".join(all_strings)
    # 移除 object replacement character (圖片佔位符)
    text = text.replace("\ufffc", "")
    # 移除控制字元（保留 \n \r \t）
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    # 將 Unicode LINE SEPARATOR / PARAGRAPH SEPARATOR 轉為普通空格
    text = text.replace("\u2028", " ").replace("\u2029", "\n")
    # 移除連續空行（保留最多一個）
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class PagesProcessor(BaseDocumentProcessor):
    """Apple Pages (.pages) 處理器"""

    @property
    def supported_extensions(self) -> List[str]:
        return [".pages"]

    def extract_text(
        self, file_bytes: bytes, filename: str = ""
    ) -> ProcessedDocument:
        """從 .pages ZIP 檔案提取文字。"""
        iwa_contents: dict[str, bytes] = {}

        try:
            with zipfile.ZipFile(BytesIO(file_bytes)) as z:
                for name in z.namelist():
                    if name.endswith(".iwa"):
                        iwa_contents[name] = z.read(name)
        except (zipfile.BadZipFile, Exception):
            pass

        if not iwa_contents:
            return ProcessedDocument(
                text_pages=[],
                metadata={"type": "pages", "source": filename},
            )

        text = _extract_text_from_iwa_files(iwa_contents)

        if not text.strip():
            return ProcessedDocument(
                text_pages=[],
                metadata={"type": "pages", "source": filename},
            )

        return ProcessedDocument(
            text_pages=[PageText(page_number=1, text=text)],
            metadata={"type": "pages", "source": filename},
        )

    def extract_text_from_directory(self, dir_path: str) -> ProcessedDocument:
        """從已解壓的 .pages 目錄提取文字。"""
        iwa_contents: dict[str, bytes] = {}
        filename = os.path.basename(dir_path)

        index_zip = os.path.join(dir_path, "Index.zip")
        if os.path.exists(index_zip):
            try:
                with zipfile.ZipFile(index_zip) as z:
                    for name in z.namelist():
                        if name.endswith(".iwa"):
                            iwa_contents[name] = z.read(name)
            except Exception:
                pass

        index_dir = os.path.join(dir_path, "Index")
        if os.path.isdir(index_dir):
            for root, _dirs, files in os.walk(index_dir):
                for f in files:
                    if f.endswith(".iwa"):
                        fp = os.path.join(root, f)
                        rel = os.path.relpath(fp, dir_path).replace("\\", "/")
                        try:
                            with open(fp, "rb") as fh:
                                iwa_contents[rel] = fh.read()
                        except Exception:
                            pass

        if not iwa_contents:
            return ProcessedDocument(
                text_pages=[],
                metadata={"type": "pages", "source": filename},
            )

        text = _extract_text_from_iwa_files(iwa_contents)

        if not text.strip():
            return ProcessedDocument(
                text_pages=[],
                metadata={"type": "pages", "source": filename},
            )

        return ProcessedDocument(
            text_pages=[PageText(page_number=1, text=text)],
            metadata={"type": "pages", "source": filename},
        )
