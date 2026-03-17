"""
向量資料庫客戶端抽象基類
所有向量資料庫連接器都必須實現這個介面
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from app.models import (
    Collection, CollectionCreate, CollectionStats,
    Vector, VectorCreate, VectorQuery, VectorSearchResult
)


class BaseVectorDBClient(ABC):
    """向量資料庫客戶端抽象基類"""
    
    def __init__(self, connection_id: str, config: Dict[str, Any]):
        self.connection_id = connection_id
        self.config = config
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @abstractmethod
    async def connect(self) -> bool:
        """建立連線"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """斷開連線"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """測試連線是否正常"""
        pass
    
    # ========== Collection 操作 ==========
    
    @abstractmethod
    async def list_collections(self) -> List[Collection]:
        """列出所有 Collections"""
        pass
    
    @abstractmethod
    async def create_collection(self, collection: CollectionCreate) -> Collection:
        """建立 Collection"""
        pass
    
    @abstractmethod
    async def get_collection(self, name: str) -> Optional[Collection]:
        """取得指定 Collection"""
        pass
    
    @abstractmethod
    async def delete_collection(self, name: str) -> None:
        """刪除 Collection"""
        pass
    
    @abstractmethod
    async def get_collection_stats(self, name: str) -> CollectionStats:
        """取得 Collection 統計資訊"""
        pass
    
    # ========== Vector 操作 ==========
    
    @abstractmethod
    async def list_vectors(
        self, 
        collection_name: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Vector]:
        """列出向量"""
        pass
    
    @abstractmethod
    async def insert_vector(
        self, 
        collection_name: str, 
        vector: VectorCreate
    ) -> Vector:
        """插入單一向量"""
        pass
    
    @abstractmethod
    async def insert_vectors(
        self, 
        collection_name: str, 
        vectors: List[VectorCreate]
    ) -> int:
        """批次插入向量，返回插入數量"""
        pass
    
    @abstractmethod
    async def get_vector(
        self, 
        collection_name: str, 
        vector_id: str
    ) -> Optional[Vector]:
        """取得單一向量"""
        pass
    
    @abstractmethod
    async def delete_vector(
        self, 
        collection_name: str, 
        vector_id: str
    ) -> None:
        """刪除向量"""
        pass
    
    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query: VectorQuery
    ) -> List[VectorSearchResult]:
        """向量相似度搜尋"""
        pass

    async def get_distinct_projects(self, collection_name: str) -> List[str]:
        """取得 collection 中所有不重複的 project 名稱（供自動篩選用）"""
        return []
