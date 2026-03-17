"""
ChromaDB 客戶端實現
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.services.base_client import BaseVectorDBClient
from app.models import (
    Collection, CollectionCreate, CollectionStats,
    Vector, VectorCreate, VectorQuery, VectorSearchResult
)


class ChromaClient(BaseVectorDBClient):
    """ChromaDB 客戶端"""
    
    def __init__(self, connection_id: str, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self.client: Optional[chromadb.ClientAPI] = None
    
    async def connect(self) -> bool:
        """建立連線"""
        try:
            host = self.config.get("host")
            port = self.config.get("port")
            persist_dir = self.config.get("persist_dir", "./data/chroma")
            
            if host and port:
                # 連接到遠端 Chroma 伺服器
                self.client = chromadb.HttpClient(host=host, port=port)
            else:
                # 使用本地持久化儲存
                self.client = chromadb.PersistentClient(path=persist_dir)
            
            # 測試連線
            self.client.heartbeat()
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise Exception(f"無法連接到 ChromaDB: {e}")
    
    async def disconnect(self) -> None:
        """斷開連線"""
        self.client = None
        self._connected = False
    
    async def test_connection(self) -> bool:
        """測試連線"""
        try:
            if self.client:
                self.client.heartbeat()
                return True
            return False
        except:
            return False
    
    # ========== Collection 操作 ==========
    
    async def list_collections(self) -> List[Collection]:
        """列出所有 Collections"""
        collections = self.client.list_collections()
        return [
            Collection(
                id=col.name,
                name=col.name,
                connection_id=self.connection_id,
                description=col.metadata.get("description") if col.metadata else None,
                metadata=col.metadata or {},
                created_at=datetime.now(),
            )
            for col in collections
        ]
    
    async def create_collection(self, collection: CollectionCreate) -> Collection:
        """建立 Collection"""
        metadata = collection.metadata or {}
        if collection.description:
            metadata["description"] = collection.description
        if collection.distance_metric:
            metadata["hnsw:space"] = collection.distance_metric
        
        col = self.client.create_collection(
            name=collection.name,
            metadata=metadata,
        )
        
        return Collection(
            id=col.name,
            name=col.name,
            connection_id=self.connection_id,
            description=collection.description,
            dimension=collection.dimension,
            distance_metric=collection.distance_metric,
            metadata=metadata,
            created_at=datetime.now(),
        )
    
    async def get_collection(self, name: str) -> Optional[Collection]:
        """取得指定 Collection"""
        try:
            col = self.client.get_collection(name)
            return Collection(
                id=col.name,
                name=col.name,
                connection_id=self.connection_id,
                description=col.metadata.get("description") if col.metadata else None,
                metadata=col.metadata or {},
                created_at=datetime.now(),
            )
        except:
            return None
    
    async def delete_collection(self, name: str) -> None:
        """刪除 Collection"""
        self.client.delete_collection(name)
    
    async def get_collection_stats(self, name: str) -> CollectionStats:
        """取得 Collection 統計資訊"""
        col = self.client.get_collection(name)
        return CollectionStats(
            vector_count=col.count(),
            dimension=None,  # Chroma 不直接暴露維度
            index_status="ready",
        )
    
    # ========== Vector 操作 ==========
    
    async def list_vectors(
        self, 
        collection_name: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Vector]:
        """列出向量"""
        col = self.client.get_collection(collection_name)
        result = col.get(
            limit=limit,
            offset=offset,
            include=["embeddings", "metadatas", "documents"]
        )
        
        vectors = []
        for i, id in enumerate(result["ids"]):
            vectors.append(Vector(
                id=id,
                collection_id=collection_name,
                embedding=result["embeddings"][i] if result["embeddings"] else [],
                metadata=result["metadatas"][i] if result["metadatas"] else {},
                document=result["documents"][i] if result["documents"] else None,
            ))
        return vectors
    
    async def insert_vector(
        self, 
        collection_name: str, 
        vector: VectorCreate
    ) -> Vector:
        """插入單一向量"""
        col = self.client.get_collection(collection_name)
        vector_id = vector.id or str(uuid.uuid4())
        
        col.add(
            ids=[vector_id],
            embeddings=[vector.embedding] if vector.embedding else None,
            metadatas=[vector.metadata] if vector.metadata else None,
            documents=[vector.document] if vector.document else None,
        )
        
        return Vector(
            id=vector_id,
            collection_id=collection_name,
            embedding=vector.embedding or [],
            metadata=vector.metadata or {},
            document=vector.document,
        )
    
    async def insert_vectors(
        self, 
        collection_name: str, 
        vectors: List[VectorCreate]
    ) -> int:
        """批次插入向量"""
        col = self.client.get_collection(collection_name)
        
        ids = [v.id or str(uuid.uuid4()) for v in vectors]
        embeddings = [v.embedding for v in vectors if v.embedding]
        metadatas = [v.metadata or {} for v in vectors]
        documents = [v.document for v in vectors if v.document]
        
        col.add(
            ids=ids,
            embeddings=embeddings if embeddings else None,
            metadatas=metadatas if metadatas else None,
            documents=documents if documents else None,
        )
        
        return len(ids)
    
    async def get_vector(
        self, 
        collection_name: str, 
        vector_id: str
    ) -> Optional[Vector]:
        """取得單一向量"""
        col = self.client.get_collection(collection_name)
        result = col.get(
            ids=[vector_id],
            include=["embeddings", "metadatas", "documents"]
        )
        
        if not result["ids"]:
            return None
        
        return Vector(
            id=result["ids"][0],
            collection_id=collection_name,
            embedding=result["embeddings"][0] if result["embeddings"] else [],
            metadata=result["metadatas"][0] if result["metadatas"] else {},
            document=result["documents"][0] if result["documents"] else None,
        )
    
    async def delete_vector(
        self, 
        collection_name: str, 
        vector_id: str
    ) -> None:
        """刪除向量"""
        col = self.client.get_collection(collection_name)
        col.delete(ids=[vector_id])
    
    async def search(
        self, 
        collection_name: str, 
        query: VectorQuery
    ) -> List[VectorSearchResult]:
        """向量相似度搜尋"""
        col = self.client.get_collection(collection_name)
        
        include = ["metadatas", "documents", "distances"]
        if query.include_embeddings:
            include.append("embeddings")
        
        if query.embedding:
            result = col.query(
                query_embeddings=[query.embedding],
                n_results=query.top_k,
                where=query.filter,
                include=include,
            )
        elif query.query_text:
            result = col.query(
                query_texts=[query.query_text],
                n_results=query.top_k,
                where=query.filter,
                include=include,
            )
        else:
            raise ValueError("必須提供 embedding 或 query_text")
        
        search_results = []
        for i, id in enumerate(result["ids"][0]):
            # Chroma 返回距離，轉換為相似度分數（1 - distance）
            distance = result["distances"][0][i] if result["distances"] else 0
            score = 1 - distance  # 簡易轉換
            
            search_results.append(VectorSearchResult(
                id=id,
                score=score,
                embedding=result["embeddings"][0][i] if result.get("embeddings") else None,
                metadata=result["metadatas"][0][i] if result["metadatas"] else None,
                document=result["documents"][0][i] if result["documents"] else None,
            ))
        
        return search_results
