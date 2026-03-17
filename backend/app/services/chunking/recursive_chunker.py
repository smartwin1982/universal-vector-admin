"""
遞迴分塊策略 — 段落 → 句子 → 字元 逐級分割
"""
import re
from typing import List

from app.services.chunking.base import BaseChunker


class RecursiveChunker(BaseChunker):
    """遞迴分塊策略"""

    # 分隔符優先序：段落 → 句子 → 子句 → 字元
    SEPARATORS = [
        "\n\n",       # 段落
        "\n",         # 換行
        "\u3002",     # 中文句號
        ". ",         # 英文句號
        "! ",         # 驚嘆號
        "? ",         # 問號
        "\uff01",     # 中文驚嘆號
        "\uff1f",     # 中文問號
        "\uff0c",     # 中文逗號
        ", ",         # 英文逗號
        " ",          # 空格
        "",           # 最後: 逐字元
    ]

    @property
    def strategy_name(self) -> str:
        return "recursive"

    def chunk(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> List[str]:
        if not text.strip():
            return []
        return self._split_recursive(text, self.SEPARATORS, chunk_size, chunk_overlap)

    def _split_recursive(
        self,
        text: str,
        separators: List[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[str]:
        final_chunks: List[str] = []

        # 找到適用的分隔符
        separator = separators[-1]
        new_separators: List[str] = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1 :]
                break

        # 用分隔符分割
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        # 合併小片段
        good_splits: List[str] = []
        current: List[str] = []
        current_len = 0

        for split in splits:
            split_text = split.strip()
            if not split_text:
                continue

            if current_len + len(split_text) + (len(separator) if current else 0) <= chunk_size:
                current.append(split_text)
                current_len += len(split_text) + (len(separator) if len(current) > 1 else 0)
            else:
                if current:
                    merged = separator.join(current) if separator else "".join(current)
                    good_splits.append(merged)

                if len(split_text) > chunk_size and new_separators:
                    # 遞迴分割大片段
                    sub_chunks = self._split_recursive(
                        split_text, new_separators, chunk_size, chunk_overlap
                    )
                    good_splits.extend(sub_chunks)
                    current = []
                    current_len = 0
                else:
                    # 加入 overlap
                    if chunk_overlap > 0 and good_splits:
                        last = good_splits[-1]
                        overlap_text = last[-chunk_overlap:] if len(last) > chunk_overlap else ""
                        if overlap_text:
                            current = [overlap_text, split_text]
                            current_len = len(overlap_text) + len(split_text)
                        else:
                            current = [split_text]
                            current_len = len(split_text)
                    else:
                        current = [split_text]
                        current_len = len(split_text)

        if current:
            merged = separator.join(current) if separator else "".join(current)
            good_splits.append(merged)

        # 過濾空白
        final_chunks = [c.strip() for c in good_splits if c.strip()]
        return final_chunks
