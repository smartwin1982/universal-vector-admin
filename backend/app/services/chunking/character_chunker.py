"""
字元分塊策略 — 重構自原有 PDFService.chunk_text()
嘗試在句子邊界切割
"""
from typing import List

from app.services.chunking.base import BaseChunker


class CharacterChunker(BaseChunker):
    """字元分塊策略（原始策略）"""

    @property
    def strategy_name(self) -> str:
        return "character"

    def chunk(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> List[str]:
        if not text.strip():
            return []

        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size

            if end >= text_len:
                chunk = text[start:].strip()
                if chunk:
                    chunks.append(chunk)
                break

            # 嘗試在句子邊界切割（往回搜尋）
            best_break = end
            search_start = max(start + chunk_size // 2, start)
            segment = text[search_start:end]

            for delimiter in ["\n\n", "\u3002", ". ", "\n", " "]:
                pos = segment.rfind(delimiter)
                if pos != -1:
                    best_break = search_start + pos + len(delimiter)
                    break

            chunk = text[start:best_break].strip()
            if chunk:
                chunks.append(chunk)

            start = best_break - chunk_overlap

        return chunks
