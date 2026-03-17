"""
向量模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class VectorBase(BaseModel):
    """向量基礎模型"""
    id: Optional[str] = Field(None, description="向量 ID")
    embedding: List[float] = Field(..., description="向量數據")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元數據")
    document: Optional[str] = Field(None, description="原始文檔")


class VectorCreate(BaseModel):
    """建立向量請求"""
    id: Optional[str] = None
    embedding: Optional[List[float]] = None  # 若有 document 可自動生成
    document: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VectorBatchCreate(BaseModel):
    """批次建立向量請求"""
    vectors: List[VectorCreate]


class VectorQuery(BaseModel):
    """向量查詢請求"""
    embedding: Optional[List[float]] = Field(None, description="查詢向量")
    query_text: Optional[str] = Field(None, description="查詢文字（會自動轉為向量）")
    top_k: int = Field(10, ge=1, le=100, description="返回數量")
    filter: Optional[Dict[str, Any]] = Field(None, description="元數據過濾條件")
    include_embeddings: bool = Field(False, description="是否返回向量數據")


class VectorSearchResult(BaseModel):
    """向量搜尋結果"""
    id: str
    score: float = Field(..., description="相似度分數")
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    document: Optional[str] = None


class Vector(VectorBase):
    """向量回應模型"""
    collection_id: str
    
    class Config:
        from_attributes = True
