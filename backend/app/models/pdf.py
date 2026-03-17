"""
PDF 上傳相關的資料模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class PDFChunkingConfig(BaseModel):
    """PDF 分塊設定"""
    chunk_size: int = Field(default=500, ge=50, le=5000, description="每個 chunk 的字元數")
    chunk_overlap: int = Field(default=50, ge=0, le=500, description="chunk 之間的重疊字元數")


class PDFChunk(BaseModel):
    """PDF 分塊結果"""
    text: str
    page_number: int
    chunk_index: int
    source_filename: str


class PDFUploadResponse(BaseModel):
    """PDF 上傳回應"""
    filename: str
    total_pages: int
    total_chunks: int
    chunks_inserted: int
    message: str
