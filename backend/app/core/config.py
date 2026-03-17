"""
應用程式配置
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """應用程式設定"""
    
    # 基本資訊
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # API 設定
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # Next.js dev
        "http://127.0.0.1:3000",
    ]
    
    # 預設向量資料庫設定
    DEFAULT_DB_TYPE: str = "chroma"  # chroma, milvus, pinecone, qdrant
    
    # Chroma 設定
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # LanceDB 設定
    LANCEDB_URI: str = "./data/lancedb"

    # Embedding 設定
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384

    # LLM 設定
    LLM_PROVIDER: str = "ollama"  # "ollama" 或 "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # RAG 設定
    RAG_SYSTEM_PROMPT: str = "你是一個有幫助的AI助手。請根據提供的文件內容回答問題。"

    # 認證設定
    AUTH_ENABLED: bool = False  # 預設關閉，生產環境設為 True
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-strong-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
