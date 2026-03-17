"""
Milvus 向量資料庫客戶端
需安裝：pip install pymilvus
"""
import uuid
from typing import List, Optional, Dict, Any

from app.models.collection import Collection, CollectionCreate, CollectionStats
from app.models.vector import Vector, VectorCreate, VectorQuery, VectorSearchResult
from app.services.base_client import BaseVectorDBClient


class MilvusClient(BaseVectorDBClient):
    """Milvus 向量資料庫客戶端"""

    def __init__(self, connection_id: str, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self._client = None

    def _ensure_lib(self):
        try:
            from pymilvus import MilvusClient as _MC
            return _MC
        except ImportError:
            raise ImportError("pymilvus is required: pip install pymilvus")

    async def connect(self) -> bool:
        _MC = self._ensure_lib()
        uri = self.config.get("uri") or self.config.get("host", "http://localhost:19530")
        token = self.config.get("api_key") or self.config.get("token", "")
        self._client = _MC(uri=uri, token=token)
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
            self._client.list_collections()
            return True
        except Exception:
            return False

    async def list_collections(self) -> List[Collection]:
        names = self._client.list_collections()
        collections = []
        for name in names:
            collections.append(Collection(
                id=name,
                name=name,
                connection_id=self.connection_id,
            ))
        return collections

    async def create_collection(self, collection: CollectionCreate) -> Collection:
        from pymilvus import DataType

        dim = collection.dimension or 384
        schema = self._client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field("id", DataType.VARCHAR, max_length=128, is_primary=True)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=dim)
        schema.add_field("document", DataType.VARCHAR, max_length=65535)

        metric = "COSINE"
        if collection.distance_metric == "euclidean":
            metric = "L2"
        elif collection.distance_metric == "dot":
            metric = "IP"

        index_params = self._client.prepare_index_params()
        index_params.add_index(field_name="embedding", metric_type=metric)

        self._client.create_collection(
            collection_name=collection.name,
            schema=schema,
            index_params=index_params,
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
        info = self._client.describe_collection(name)
        return Collection(
            id=name,
            name=name,
            connection_id=self.connection_id,
        )

    async def delete_collection(self, name: str) -> bool:
        self._client.drop_collection(name)
        return True

    async def get_collection_stats(self, name: str) -> CollectionStats:
        count = self._client.get_collection_stats(name).get("row_count", 0)
        return CollectionStats(vector_count=count)

    async def list_vectors(self, collection_name: str, limit: int = 100, offset: int = 0) -> List[Vector]:
        results = self._client.query(
            collection_name=collection_name,
            filter="",
            limit=limit,
            offset=offset,
            output_fields=["id", "document", "embedding"],
        )
        vectors = []
        for row in results:
            vectors.append(Vector(
                id=str(row.get("id", "")),
                collection_id=collection_name,
                embedding=row.get("embedding", []),
                metadata={k: v for k, v in row.items() if k not in ("id", "embedding", "document")},
                document=row.get("document", ""),
            ))
        return vectors

    async def insert_vector(self, collection_name: str, vector: VectorCreate) -> str:
        vid = vector.id or str(uuid.uuid4())
        data = {
            "id": vid,
            "embedding": vector.embedding or [],
            "document": vector.document or "",
        }
        if vector.metadata:
            data.update(vector.metadata)

        self._client.insert(collection_name=collection_name, data=[data])
        return vid

    async def insert_vectors(self, collection_name: str, vectors: List[VectorCreate]) -> int:
        data = []
        for v in vectors:
            row = {
                "id": v.id or str(uuid.uuid4()),
                "embedding": v.embedding or [],
                "document": v.document or "",
            }
            if v.metadata:
                row.update(v.metadata)
            data.append(row)

        self._client.insert(collection_name=collection_name, data=data)
        return len(data)

    async def get_vector(self, collection_name: str, vector_id: str) -> Optional[Vector]:
        results = self._client.get(
            collection_name=collection_name,
            ids=[vector_id],
            output_fields=["id", "document", "embedding"],
        )
        if not results:
            return None
        row = results[0]
        return Vector(
            id=str(row.get("id", "")),
            collection_id=collection_name,
            embedding=row.get("embedding", []),
            document=row.get("document", ""),
        )

    async def delete_vector(self, collection_name: str, vector_id: str) -> bool:
        self._client.delete(collection_name=collection_name, ids=[vector_id])
        return True

    async def search(self, collection_name: str, query: VectorQuery) -> List[VectorSearchResult]:
        results = self._client.search(
            collection_name=collection_name,
            data=[query.embedding or []],
            limit=query.top_k or 10,
            output_fields=["id", "document"],
        )

        search_results = []
        if results and len(results) > 0:
            for hit in results[0]:
                search_results.append(VectorSearchResult(
                    id=str(hit.get("id", "")),
                    score=float(hit.get("distance", 0)),
                    document=hit.get("entity", {}).get("document", ""),
                    metadata={},
                ))
        return search_results
