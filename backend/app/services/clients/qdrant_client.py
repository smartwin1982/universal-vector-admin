"""
Qdrant 向量資料庫客戶端
需安裝：pip install qdrant-client
"""
import uuid
from typing import List, Optional, Dict, Any

from app.models.collection import Collection, CollectionCreate, CollectionStats
from app.models.vector import Vector, VectorCreate, VectorQuery, VectorSearchResult
from app.services.base_client import BaseVectorDBClient


class QdrantClient(BaseVectorDBClient):
    """Qdrant 向量資料庫客戶端"""

    def __init__(self, connection_id: str, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self._client = None

    def _ensure_lib(self):
        try:
            from qdrant_client import QdrantClient as _QC
            from qdrant_client.models import Distance, VectorParams, PointStruct
            return _QC, Distance, VectorParams, PointStruct
        except ImportError:
            raise ImportError("qdrant-client is required: pip install qdrant-client")

    async def connect(self) -> bool:
        _QC, *_ = self._ensure_lib()
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 6333)
        api_key = self.config.get("api_key")
        url = self.config.get("url")

        if url:
            self._client = _QC(url=url, api_key=api_key)
        else:
            self._client = _QC(host=host, port=port, api_key=api_key)

        self._connected = True
        return True

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()
        self._connected = False

    async def test_connection(self) -> bool:
        try:
            if not self._client:
                await self.connect()
            self._client.get_collections()
            return True
        except Exception:
            return False

    async def list_collections(self) -> List[Collection]:
        result = self._client.get_collections()
        collections = []
        for col in result.collections:
            info = self._client.get_collection(col.name)
            collections.append(Collection(
                id=col.name,
                name=col.name,
                connection_id=self.connection_id,
                dimension=info.config.params.vectors.size if info.config.params.vectors else None,
            ))
        return collections

    async def create_collection(self, collection: CollectionCreate) -> Collection:
        _, Distance, VectorParams, _ = self._ensure_lib()
        dim = collection.dimension or 384
        distance = Distance.COSINE
        if collection.distance_metric == "euclidean":
            distance = Distance.EUCLID
        elif collection.distance_metric == "dot":
            distance = Distance.DOT

        self._client.create_collection(
            collection_name=collection.name,
            vectors_config=VectorParams(size=dim, distance=distance),
        )
        return Collection(
            id=collection.name,
            name=collection.name,
            connection_id=self.connection_id,
            description=collection.description,
            dimension=dim,
            distance_metric=collection.distance_metric,
        )

    async def get_collection(self, name: str) -> Collection:
        info = self._client.get_collection(name)
        return Collection(
            id=name,
            name=name,
            connection_id=self.connection_id,
            dimension=info.config.params.vectors.size if info.config.params.vectors else None,
        )

    async def delete_collection(self, name: str) -> bool:
        self._client.delete_collection(name)
        return True

    async def get_collection_stats(self, name: str) -> CollectionStats:
        info = self._client.get_collection(name)
        return CollectionStats(
            vector_count=info.points_count or 0,
            dimension=info.config.params.vectors.size if info.config.params.vectors else None,
        )

    async def list_vectors(self, collection_name: str, limit: int = 100, offset: int = 0) -> List[Vector]:
        result = self._client.scroll(
            collection_name=collection_name,
            limit=limit,
            offset=offset if offset else None,
            with_vectors=True,
            with_payload=True,
        )
        vectors = []
        for point in result[0]:
            vectors.append(Vector(
                id=str(point.id),
                collection_id=collection_name,
                embedding=point.vector if point.vector else [],
                metadata=dict(point.payload) if point.payload else {},
                document=point.payload.get("document", "") if point.payload else "",
            ))
        return vectors

    async def insert_vector(self, collection_name: str, vector: VectorCreate) -> str:
        _, _, _, PointStruct = self._ensure_lib()
        vid = vector.id or str(uuid.uuid4())
        payload = dict(vector.metadata) if vector.metadata else {}
        if vector.document:
            payload["document"] = vector.document

        self._client.upsert(
            collection_name=collection_name,
            points=[PointStruct(
                id=vid,
                vector=vector.embedding or [],
                payload=payload,
            )],
        )
        return vid

    async def insert_vectors(self, collection_name: str, vectors: List[VectorCreate]) -> int:
        _, _, _, PointStruct = self._ensure_lib()
        points = []
        for v in vectors:
            vid = v.id or str(uuid.uuid4())
            payload = dict(v.metadata) if v.metadata else {}
            if v.document:
                payload["document"] = v.document
            points.append(PointStruct(id=vid, vector=v.embedding or [], payload=payload))

        self._client.upsert(collection_name=collection_name, points=points)
        return len(points)

    async def get_vector(self, collection_name: str, vector_id: str) -> Optional[Vector]:
        results = self._client.retrieve(
            collection_name=collection_name,
            ids=[vector_id],
            with_vectors=True,
            with_payload=True,
        )
        if not results:
            return None
        point = results[0]
        return Vector(
            id=str(point.id),
            collection_id=collection_name,
            embedding=point.vector if point.vector else [],
            metadata=dict(point.payload) if point.payload else {},
            document=point.payload.get("document", "") if point.payload else "",
        )

    async def delete_vector(self, collection_name: str, vector_id: str) -> bool:
        self._client.delete(
            collection_name=collection_name,
            points_selector=[vector_id],
        )
        return True

    async def search(self, collection_name: str, query: VectorQuery) -> List[VectorSearchResult]:
        results = self._client.search(
            collection_name=collection_name,
            query_vector=query.embedding or [],
            limit=query.top_k or 10,
            with_payload=True,
            with_vectors=query.include_embeddings or False,
        )
        search_results = []
        for hit in results:
            search_results.append(VectorSearchResult(
                id=str(hit.id),
                score=hit.score,
                embedding=hit.vector if hit.vector else None,
                metadata=dict(hit.payload) if hit.payload else {},
                document=hit.payload.get("document", "") if hit.payload else "",
            ))
        return search_results
