"""
語意分塊策略 — 基於 embedding 相似度決定分割點
先用句子作為基本單位，相鄰句子相似度低於閾值時切割
"""
import re
from typing import List

from app.services.chunking.base import BaseChunker


class SemanticChunker(BaseChunker):
    """語意分塊策略"""

    def __init__(self, similarity_threshold: float = 0.5):
        self._threshold = similarity_threshold

    @property
    def strategy_name(self) -> str:
        return "semantic"

    def chunk(
        self,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> List[str]:
        if not text.strip():
            return []

        # 1. 分句
        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return [text.strip()] if text.strip() else []

        # 2. 計算相鄰句子的 embedding 相似度
        from app.services.embedding_service import embedding_service

        embeddings = embedding_service.embed_batch(sentences)

        # 3. 找分割點（相似度低於閾值的位置）
        breakpoints: List[int] = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            if sim < self._threshold:
                breakpoints.append(i + 1)

        # 4. 按分割點組合段落
        chunks: List[str] = []
        start = 0
        for bp in breakpoints:
            chunk_text = " ".join(sentences[start:bp]).strip()
            if chunk_text:
                # 如果 chunk 太大，進一步分割
                if len(chunk_text) > chunk_size * 2:
                    sub_chunks = self._force_split(chunk_text, chunk_size)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chunk_text)
            start = bp

        # 最後一段
        remaining = " ".join(sentences[start:]).strip()
        if remaining:
            if len(remaining) > chunk_size * 2:
                chunks.extend(self._force_split(remaining, chunk_size))
            else:
                chunks.append(remaining)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """分句（支援中英文）"""
        # 使用正則分割中英文句子
        pattern = r'(?<=[。！？.!?\n])\s*'
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """計算兩個向量的 cosine 相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _force_split(self, text: str, chunk_size: int) -> List[str]:
        """強制按字元數分割"""
        chunks: List[str] = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size].strip()
            if chunk:
                chunks.append(chunk)
        return chunks
