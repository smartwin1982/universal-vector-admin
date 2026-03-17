"""
RAG 問答相關的資料模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class RAGAskRequest(BaseModel):
    """RAG 問答請求"""
    question: str = Field(..., min_length=1, description="使用者的問題")
    connection_id: str = Field(..., description="向量資料庫連線 ID")
    collection_name: str = Field(..., description="Collection 名稱")
    top_k: int = Field(default=5, ge=1, le=20, description="檢索的文件數量")
    llm_provider: Optional[str] = Field(default=None, description="指定 LLM provider（ollama 或 gemini），預設使用 .env 設定")
    session_id: Optional[str] = Field(default=None, description="對話 Session ID，提供時啟用對話記憶")
    project: Optional[str] = Field(default=None, description="專案名稱篩選（前綴匹配）")


class RAGSourceDocument(BaseModel):
    """RAG 參考來源文件"""
    id: str
    document: str
    score: float


class RAGAskResponse(BaseModel):
    """RAG 問答回應"""
    answer: str
    sources: List[RAGSourceDocument]
    llm_provider: str
