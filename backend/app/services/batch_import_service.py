"""
批次目錄匯入服務
掃描伺服器端目錄，將所有支援格式的檔案匯入向量資料庫
"""
import os
import re
import json
import traceback
from typing import AsyncGenerator

from app.models.document import (
    BatchScanRequest,
    BatchScanFileInfo,
    BatchScanResponse,
    BatchImportRequest,
    DocumentChunk,
)
from app.models.vector import VectorCreate
from app.models import CollectionCreate
from app.services.document_processors import get_processor, get_supported_extensions
from app.services.chunking import get_chunker
from app.services.embedding_service import embedding_service
from app.services.connection_manager import ConnectionManager

EMBED_BATCH_SIZE = 64

# 要過濾的系統檔案 pattern
_SKIP_PATTERNS = {".DS_Store", "Thumbs.db", "desktop.ini"}


class BatchImportService:
    """批次目錄匯入服務"""

    def __init__(self):
        self.connection_manager = ConnectionManager()

    def scan_directory(self, req: BatchScanRequest) -> BatchScanResponse:
        """掃描目錄，回傳所有支援格式的檔案清單"""
        directory = req.directory_path
        if not os.path.isdir(directory):
            raise ValueError(f"目錄不存在：{directory}")

        supported_exts = set(get_supported_extensions())  # e.g. {".pdf", ".docx", ...}
        files: list[BatchScanFileInfo] = []
        subdirs: set[str] = set()

        # 已解壓的 iWork 目錄副檔名（如 xxx.pages/ 目錄）
        _iwork_dir_exts = {".pages", ".key"}

        for root, dirs, filenames in os.walk(directory):
            # 跳過隱藏目錄
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            # 偵測已解壓的 .pages / .key 目錄（裡面有 Index.zip 或 Index/）
            iwork_dirs = []
            remaining_dirs = []
            for d in dirs:
                d_ext = ""
                if "." in d:
                    d_ext = "." + d.rsplit(".", 1)[-1].lower()
                dir_path = os.path.join(root, d)
                if d_ext in _iwork_dir_exts and (
                    os.path.exists(os.path.join(dir_path, "Index.zip"))
                    or os.path.isdir(os.path.join(dir_path, "Index"))
                ):
                    iwork_dirs.append(d)
                else:
                    remaining_dirs.append(d)

            # 不要 walk 進已解壓的 iWork 目錄
            dirs[:] = remaining_dirs

            # 將已解壓的 iWork 目錄當作檔案加入清單
            for d in iwork_dirs:
                d_ext = "." + d.rsplit(".", 1)[-1].lower()
                if d_ext not in supported_exts:
                    continue
                dir_path = os.path.join(root, d)
                rel_path = os.path.relpath(dir_path, directory).replace("\\", "/")
                parts = rel_path.split("/")
                subdir = parts[0] if len(parts) > 1 else ""
                # 估算目錄大小
                total_size = 0
                for dp, _, fns in os.walk(dir_path):
                    for fn in fns:
                        try:
                            total_size += os.path.getsize(os.path.join(dp, fn))
                        except OSError:
                            pass
                if subdir:
                    subdirs.add(subdir)
                files.append(BatchScanFileInfo(
                    relative_path=rel_path,
                    filename=d,
                    extension=d_ext,
                    file_size=total_size,
                    subdirectory=subdir,
                ))

            for fname in filenames:
                # 跳過系統檔
                if fname in _SKIP_PATTERNS or fname.startswith("._"):
                    continue

                ext = ""
                if "." in fname:
                    ext = "." + fname.rsplit(".", 1)[-1].lower()

                if ext not in supported_exts:
                    continue

                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, directory)
                # 正規化路徑分隔符
                rel_path = rel_path.replace("\\", "/")

                # 判斷第一層子目錄
                parts = rel_path.split("/")
                subdir = parts[0] if len(parts) > 1 else ""

                try:
                    file_size = os.path.getsize(full_path)
                except OSError:
                    file_size = 0

                if subdir:
                    subdirs.add(subdir)

                files.append(BatchScanFileInfo(
                    relative_path=rel_path,
                    filename=fname,
                    extension=ext,
                    file_size=file_size,
                    subdirectory=subdir,
                ))

        return BatchScanResponse(
            directory_path=directory,
            total_files=len(files),
            files=files,
            subdirectories=sorted(subdirs),
            supported_extensions=sorted(supported_exts),
        )

    async def import_stream(self, req: BatchImportRequest) -> AsyncGenerator[str, None]:
        """非同步產生器，產出 SSE 事件"""

        def sse(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        # 取得 DB client
        client = self.connection_manager.get_client(req.connection_id)
        if not client:
            yield sse("error", {"message": "連線不存在或未連線"})
            return

        # 掃描目錄
        try:
            scan_req = BatchScanRequest(
                directory_path=req.directory_path,
                connection_id=req.connection_id,
            )
            scan_result = self.scan_directory(scan_req)
        except Exception as e:
            yield sse("error", {"message": f"掃描失敗：{str(e)}"})
            return

        total_files = scan_result.total_files
        if total_files == 0:
            yield sse("done", {"total_files": 0, "success": 0, "failed": 0, "total_chunks": 0})
            return

        yield sse("scan_complete", {"total_files": total_files})

        # 取得分塊器
        chunker = get_chunker(req.strategy.value)

        # 追蹤已建立的 collection
        created_collections: set[str] = set()
        success_count = 0
        failed_count = 0
        total_chunks_inserted = 0

        for idx, file_info in enumerate(scan_result.files):
            # 決定目標 collection
            if req.mapping_mode.value == "auto" and file_info.subdirectory:
                target_collection = self._sanitize_collection_name(file_info.subdirectory)
            elif req.mapping_mode.value == "auto" and not file_info.subdirectory:
                target_collection = req.default_collection or req.collection_name
            else:
                target_collection = req.collection_name

            if not target_collection:
                yield sse("file_error", {
                    "index": idx,
                    "filename": file_info.filename,
                    "error": "未指定目標 collection",
                })
                failed_count += 1
                continue

            yield sse("file_start", {
                "index": idx,
                "filename": file_info.filename,
                "collection": target_collection,
                "total": total_files,
            })

            # 確保 collection 存在
            if target_collection not in created_collections:
                try:
                    existing = await client.get_collection(target_collection)
                    if not existing:
                        await client.create_collection(CollectionCreate(name=target_collection))
                        yield sse("collection_created", {"name": target_collection})
                    created_collections.add(target_collection)
                except Exception:
                    # collection 可能已存在（get_collection 在某些 DB 會拋例外）
                    try:
                        await client.create_collection(CollectionCreate(name=target_collection))
                        yield sse("collection_created", {"name": target_collection})
                    except Exception:
                        pass
                    created_collections.add(target_collection)

            # 處理檔案
            full_path = os.path.join(req.directory_path, file_info.relative_path)
            try:
                processor = get_processor(file_info.filename)
                if not processor:
                    yield sse("file_error", {
                        "index": idx,
                        "filename": file_info.filename,
                        "error": "無法找到對應的處理器",
                    })
                    failed_count += 1
                    continue

                # 已解壓的 .pages/.key 目錄：使用 extract_text_from_directory
                if os.path.isdir(full_path) and hasattr(processor, "extract_text_from_directory"):
                    doc = processor.extract_text_from_directory(full_path)
                else:
                    with open(full_path, "rb") as f:
                        file_bytes = f.read()

                    if not file_bytes:
                        yield sse("file_error", {
                            "index": idx,
                            "filename": file_info.filename,
                            "error": "檔案為空",
                        })
                        failed_count += 1
                        continue

                    doc = processor.extract_text(file_bytes, file_info.filename)

                # 分塊
                all_chunks: list[DocumentChunk] = []
                chunk_index = 0
                for page in doc.text_pages:
                    text_chunks = chunker.chunk(page.text, req.chunk_size, req.chunk_overlap)
                    for text in text_chunks:
                        all_chunks.append(DocumentChunk(
                            text=text,
                            page_number=page.page_number,
                            chunk_index=chunk_index,
                            source_filename=file_info.filename,
                        ))
                        chunk_index += 1

                if not all_chunks:
                    yield sse("file_error", {
                        "index": idx,
                        "filename": file_info.filename,
                        "error": "分塊後無有效內容",
                    })
                    failed_count += 1
                    continue

                # 批次 embed + 寫入
                file_type = doc.metadata.get("type", "unknown")
                file_chunks_inserted = 0

                for i in range(0, len(all_chunks), EMBED_BATCH_SIZE):
                    batch = all_chunks[i: i + EMBED_BATCH_SIZE]
                    texts = [c.text for c in batch]
                    embeddings = embedding_service.embed_batch(texts)

                    vectors = [
                        VectorCreate(
                            document=chunk.text,
                            embedding=emb,
                            metadata={
                                "source": chunk.source_filename,
                                "page": chunk.page_number,
                                "chunk_index": chunk.chunk_index,
                                "type": file_type,
                                **({"project": req.project} if req.project else {}),
                            },
                        )
                        for chunk, emb in zip(batch, embeddings)
                    ]

                    count = await client.insert_vectors(target_collection, vectors)
                    file_chunks_inserted += count

                total_chunks_inserted += file_chunks_inserted
                success_count += 1

                yield sse("file_done", {
                    "index": idx,
                    "filename": file_info.filename,
                    "pages": len(doc.text_pages),
                    "chunks_inserted": file_chunks_inserted,
                })

            except Exception as e:
                traceback.print_exc()
                yield sse("file_error", {
                    "index": idx,
                    "filename": file_info.filename,
                    "error": str(e),
                })
                failed_count += 1

        yield sse("done", {
            "total_files": total_files,
            "success": success_count,
            "failed": failed_count,
            "total_chunks": total_chunks_inserted,
        })

    @staticmethod
    def _sanitize_collection_name(name: str) -> str:
        """將目錄名稱轉為合法的 collection 名稱"""
        # 替換非英數字元為底線
        sanitized = re.sub(r"[^\w\-]", "_", name)
        # 移除連續底線
        sanitized = re.sub(r"_+", "_", sanitized)
        # 移除首尾底線
        sanitized = sanitized.strip("_")
        # 確保不為空
        if not sanitized:
            sanitized = "default"
        return sanitized.lower()
