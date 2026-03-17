"""
使用者認證相關資料模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    """使用者"""
    username: str
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)


class UserCreate(BaseModel):
    """使用者註冊請求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """使用者登入請求"""
    username: str
    password: str


class Token(BaseModel):
    """JWT Token 回應"""
    access_token: str
    token_type: str = "bearer"
    username: str


class UserInfo(BaseModel):
    """使用者資訊（不含密碼）"""
    username: str
    created_at: str
