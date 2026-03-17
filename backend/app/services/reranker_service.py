"""
Reranker 服務 — 使用 cross-encoder 模型對搜尋結果重新排序
"""
import logging
from typing import List, Optional

from app.models.vector import VectorSearchResult

logger = logging.getLogger(__name__)


class RerankerService:
    """Cross-encoder Reranker 服務（Singleton）"""

    _instance: "RerankerService | None" = None
    _model = None

    def __new__(cls) -> "RerankerService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
                logger.info(f"[Reranker] 載入模型: {model_name}")
                self._model = CrossEncoder(model_name)
                logger.info("[Reranker] 模型載入完成")
            except Exception as e:
                logger.error(f"[Reranker] 模型載入失敗: {e}")
                raise

    def rerank(
        self,
        query: str,
        results: List[VectorSearchResult],
        top_k: Optional[int] = None,
    ) -> List[VectorSearchResult]:
        """
        使用 cross-encoder 重新排序搜尋結果

        Args:
            query: 搜尋查詢
            results: 原始搜尋結果
            top_k: 重排後取前 k 個（None 表示全部）

        Returns:
            重新排序的搜尋結果
        """
        if not results:
            return results

        self._ensure_model()

        # 準備 cross-encoder 輸入
        pairs = [(query, r.document or "") for r in results]
        scores = self._model.predict(pairs)

        # 將 cross-encoder 分數更新到結果中
        scored_results = []
        for result, ce_score in zip(results, scores):
            scored_results.append(VectorSearchResult(
                id=result.id,
                score=float(ce_score),
                embedding=result.embedding,
                metadata=result.metadata,
                document=result.document,
            ))

        # 按新分數降序排列
        scored_results.sort(key=lambda r: r.score, reverse=True)

        if top_k:
            scored_results = scored_results[:top_k]

        return scored_results


reranker_service = RerankerService()
