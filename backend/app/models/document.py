"""
統一文件上傳相關的資料模型
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ChunkingStrategy(str, Enum):
    """分塊策略"""
    character = "character"
    recursive = "recursive"
    semantic = "semantic"


class DocumentChunkingConfig(BaseModel):
    """文件分塊設定"""
    chunk_size: int = Field(default=500, ge=50, le=5000, description="每個 chunk 的字元數")
    chunk_overlap: int = Field(default=50, ge=0, le=500, description="chunk 之間的重疊字元數")
    strategy: ChunkingStrategy = Field(default=ChunkingStrategy.recursive, description="分塊策略")


class DocumentChunk(BaseModel):
    """文件分塊結果"""
    text: str
    page_number: int
    chunk_index: int
    source_filename: str


class DocumentUploadResponse(BaseModel):
    """統一文件上傳回應"""
    filename: str
    file_type: str
    total_pages: int
    total_chunks: int
    chunks_inserted: int
    chunking_strategy: str
    message: str


class WebScrapeRequest(BaseModel):
    """網頁擷取請求"""
    url: str = Field(..., description="要擷取的網頁 URL")
    connection_id: str = Field(..., description="向量資料庫連線 ID")
    collection_name: str = Field(..., description="Collection 名稱")
    chunk_size: int = Field(default=500, ge=50, le=5000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    strategy: ChunkingStrategy = Field(default=ChunkingStrategy.recursive)
    project: Optional[str] = Field(default=None, description="專案名稱")


# ========== 批次目錄匯入 ==========


class CollectionMappingMode(str, Enum):
    """Collection 映射模式"""
    single = "single"   # 全部匯入同一 collection
    auto = "auto"       # 依子目錄自動分類


class BatchScanRequest(BaseModel):
    """批次掃描請求"""
    directory_path: str = Field(..., description="要掃描的目錄路徑")
    connection_id: str = Field(..., description="向量資料庫連線 ID")


class BatchScanFileInfo(BaseModel):
    """掃描到的檔案資訊"""
    relative_path: str
    filename: str
    extension: str
    file_size: int
    subdirectory: str = Field(default="", description="所屬第一層子目錄（根目錄為空字串）")


class BatchScanResponse(BaseModel):
    """批次掃描回應"""
    directory_path: str
    total_files: int
    files: List[BatchScanFileInfo]
    subdirectories: List[str]
    supported_extensions: List[str]


class BatchImportRequest(BaseModel):
    """批次匯入請求"""
    directory_path: str = Field(..., description="目錄路徑")
    connection_id: str = Field(..., description="向量資料庫連線 ID")
    collection_name: str = Field(default="", description="目標 collection（single 模式必填）")
    mapping_mode: CollectionMappingMode = Field(default=CollectionMappingMode.single)
    default_collection: str = Field(default="", description="auto 模式下根目錄檔案的預設 collection")
    chunk_size: int = Field(default=500, ge=50, le=5000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    strategy: ChunkingStrategy = Field(default=ChunkingStrategy.recursive)
    project: Optional[str] = Field(default=None, description="專案名稱")
