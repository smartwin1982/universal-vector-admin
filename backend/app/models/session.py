"""
對話 Session 相關的資料模型
"""
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """單一對話訊息"""
    role: str = Field(..., description="角色：user 或 assistant")
    content: str = Field(..., description="訊息內容")
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationSession(BaseModel):
    """對話 Session"""
    session_id: str
    messages: List[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ConversationSessionResponse(BaseModel):
    """對話 Session API 回應"""
    session_id: str
    messages: List[dict]
    created_at: str
    updated_at: str
