"""
連線模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime


DBType = Literal["chroma", "lancedb", "milvus", "pinecone", "qdrant", "weaviate", "pgvector"]


class ConnectionBase(BaseModel):
    """連線基礎模型"""
    name: str = Field(..., description="連線名稱")
    db_type: DBType = Field(..., description="資料庫類型")
    host: Optional[str] = Field(None, description="主機位址")
    port: Optional[int] = Field(None, description="連接埠")
    api_key: Optional[str] = Field(None, description="API Key")
    extra_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="額外配置")


class ConnectionCreate(ConnectionBase):
    """建立連線請求"""
    pass


class ConnectionTest(BaseModel):
    """測試連線請求"""
    db_type: DBType
    host: Optional[str] = None
    port: Optional[int] = None
    api_key: Optional[str] = None
    extra_config: Optional[Dict[str, Any]] = None


class Connection(ConnectionBase):
    """連線回應模型"""
    id: str = Field(..., description="連線 ID")
    is_connected: bool = Field(default=False, description="是否已連線")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
