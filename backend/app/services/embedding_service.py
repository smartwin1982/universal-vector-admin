"""
Embedding Service — 使用 sentence-transformers 產生文字向量
"""
from typing import List
from sentence_transformers import SentenceTransformer
from app.core.config import settings


class EmbeddingService:
    """Singleton embedding service，啟動時載入模型一次"""

    _instance: "EmbeddingService | None" = None
    _model: SentenceTransformer | None = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return self._model

    def embed(self, text: str) -> List[float]:
        """單筆文字轉為 embedding"""
        model = self._get_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批次文字轉為 embedding"""
        model = self._get_model()
        vectors = model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()


# 模組層級 singleton 實例
embedding_service = EmbeddingService()
