"""
Collection 模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class CollectionBase(BaseModel):
    """Collection 基礎模型"""
    name: str = Field(..., description="Collection 名稱")
    description: Optional[str] = Field(None, description="描述")
    dimension: Optional[int] = Field(None, description="向量維度")
    distance_metric: Optional[str] = Field("cosine", description="距離度量方式")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CollectionCreate(CollectionBase):
    """建立 Collection 請求"""
    pass


class CollectionStats(BaseModel):
    """Collection 統計資訊"""
    vector_count: int = Field(0, description="向量數量")
    dimension: Optional[int] = Field(None, description="向量維度")
    index_status: Optional[str] = Field(None, description="索引狀態")


class Collection(CollectionBase):
    """Collection 回應模型"""
    id: str = Field(..., description="Collection ID")
    connection_id: str = Field(..., description="所屬連線 ID")
    stats: Optional[CollectionStats] = None
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True
