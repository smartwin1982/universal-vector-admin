"""
LanceDB 客戶端實現
"""
import lancedb
import pyarrow as pa
import pyarrow.compute as pc
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json

from app.services.base_client import BaseVectorDBClient
from app.models import (
    Collection, CollectionCreate, CollectionStats,
    Vector, VectorCreate, VectorQuery, VectorSearchResult
)


class LanceDBClient(BaseVectorDBClient):
    """LanceDB 客戶端"""

    def __init__(self, connection_id: str, config: Dict[str, Any]):
        super().__init__(connection_id, config)
        self.db = None

    async def connect(self) -> bool:
        """建立連線"""
        try:
            uri = self.config.get("uri")
            api_key = self.config.get("api_key")
            persist_dir = self.config.get("persist_dir", "./data/lancedb")

            if uri:
                # 使用指定的 URI（支援 LanceDB Cloud 或自訂路徑）
                connect_kwargs = {"uri": uri}
                if api_key:
                    connect_kwargs["api_key"] = api_key
                self.db = lancedb.connect(**connect_kwargs)
            else:
                # 使用本地持久化儲存
                self.db = lancedb.connect(persist_dir)

            # 測試連線：列出 tables
            self.db.table_names()
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise Exception(f"無法連接到 LanceDB: {e}")

    async def disconnect(self) -> None:
        """斷開連線"""
        self.db = None
        self._connected = False

    async def test_connection(self) -> bool:
        """測試連線"""
        try:
            if self.db:
                self.db.table_names()
                return True
            return False
        except:
            return False

    # ========== 內部工具方法 ==========

    def _get_table_metadata(self, table_name: str) -> Dict[str, Any]:
        """從 table 的 schema metadata 取得自定義元數據"""
        try:
            table = self.db.open_table(table_name)
            schema = table.schema
            metadata = {}
            if schema.metadata:
                for key, value in schema.metadata.items():
                    decoded_key = key.decode("utf-8") if isinstance(key, bytes) else key
                    decoded_value = value.decode("utf-8") if isinstance(value, bytes) else value
                    if decoded_key.startswith("uva_"):
                        metadata[decoded_key[4:]] = decoded_value
            return metadata
        except:
            return {}

    def _parse_metadata_json(self, raw: Any) -> Dict[str, Any]:
        """解析 metadata JSON 字串"""
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except:
            return {}

    def _row_to_vector(self, row: Dict[str, Any], collection_name: str) -> Vector:
        """將 LanceDB row 轉換為 Vector 模型"""
        return Vector(
            id=row["id"],
            collection_id=collection_name,
            embedding=row.get("vector", []),
            metadata=self._parse_metadata_json(row.get("metadata_json")),
            document=row.get("document"),
        )

    # ========== Collection 操作 ==========

    async def list_collections(self) -> List[Collection]:
        """列出所有 Collections"""
        table_names = self.db.table_names()
        collections = []
        for name in table_names:
            meta = self._get_table_metadata(name)
            collections.append(Collection(
                id=name,
                name=name,
                connection_id=self.connection_id,
                description=meta.get("description"),
                metadata=meta,
                created_at=datetime.now(),
            ))
        return collections

    async def create_collection(self, collection: CollectionCreate) -> Collection:
        """建立 Collection"""
        dimension = collection.dimension
        if not dimension:
            raise ValueError("LanceDB 建立 Collection 時必須指定向量維度 (dimension)")

        distance_metric = collection.distance_metric or "cosine"

        # 建立 PyArrow schema
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), list_size=dimension)),
            pa.field("document", pa.string()),
            pa.field("metadata_json", pa.string()),
        ])

        # 將自定義元數據存入 schema metadata（以 uva_ 前綴區分）
        custom_meta = {
            b"uva_distance_metric": distance_metric.encode("utf-8"),
            b"uva_dimension": str(dimension).encode("utf-8"),
        }
        if collection.description:
            custom_meta[b"uva_description"] = collection.description.encode("utf-8")
        if collection.metadata:
            custom_meta[b"uva_metadata"] = json.dumps(collection.metadata).encode("utf-8")

        schema = schema.with_metadata(custom_meta)

        self.db.create_table(collection.name, schema=schema)

        return Collection(
            id=collection.name,
            name=collection.name,
            connection_id=self.connection_id,
            description=collection.description,
            dimension=dimension,
            distance_metric=distance_metric,
            metadata=collection.metadata or {},
            created_at=datetime.now(),
        )

    async def get_collection(self, name: str) -> Optional[Collection]:
        """取得指定 Collection"""
        try:
            if name not in self.db.table_names():
                return None
            meta = self._get_table_metadata(name)
            return Collection(
                id=name,
                name=name,
                connection_id=self.connection_id,
                description=meta.get("description"),
                dimension=int(meta["dimension"]) if meta.get("dimension") else None,
                metadata=meta,
                created_at=datetime.now(),
            )
        except:
            return None

    async def delete_collection(self, name: str) -> None:
        """刪除 Collection"""
        self.db.drop_table(name)

    async def get_collection_stats(self, name: str) -> CollectionStats:
        """取得 Collection 統計資訊"""
        table = self.db.open_table(name)
        count = table.count_rows()
        meta = self._get_table_metadata(name)
        return CollectionStats(
            vector_count=count,
            dimension=int(meta["dimension"]) if meta.get("dimension") else None,
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
        table = self.db.open_table(collection_name)
        arrow_table = table.to_arrow()
        total = arrow_table.num_rows

        if offset >= total:
            return []

        actual_limit = min(limit, total - offset)
        sliced = arrow_table.slice(offset, actual_limit)
        rows = sliced.to_pylist()

        return [self._row_to_vector(row, collection_name) for row in rows]

    async def insert_vector(
        self,
        collection_name: str,
        vector: VectorCreate
    ) -> Vector:
        """插入單一向量"""
        table = self.db.open_table(collection_name)
        vector_id = vector.id or str(uuid.uuid4())

        row = {
            "id": vector_id,
            "vector": vector.embedding or [],
            "document": vector.document or "",
            "metadata_json": json.dumps(vector.metadata) if vector.metadata else "{}",
        }

        table.add([row])

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
        table = self.db.open_table(collection_name)

        rows = []
        for v in vectors:
            rows.append({
                "id": v.id or str(uuid.uuid4()),
                "vector": v.embedding or [],
                "document": v.document or "",
                "metadata_json": json.dumps(v.metadata) if v.metadata else "{}",
            })

        table.add(rows)
        return len(rows)

    async def get_vector(
        self,
        collection_name: str,
        vector_id: str
    ) -> Optional[Vector]:
        """取得單一向量"""
        table = self.db.open_table(collection_name)
        arrow_table = table.to_arrow()

        mask = pc.equal(arrow_table.column("id"), vector_id)
        filtered = arrow_table.filter(mask)

        if filtered.num_rows == 0:
            return None

        row = filtered.to_pylist()[0]
        return self._row_to_vector(row, collection_name)

    async def delete_vector(
        self,
        collection_name: str,
        vector_id: str
    ) -> None:
        """刪除向量"""
        table = self.db.open_table(collection_name)
        table.delete(f'id = "{vector_id}"')

    async def search(
        self,
        collection_name: str,
        query: VectorQuery
    ) -> List[VectorSearchResult]:
        """向量相似度搜尋"""
        if not query.embedding:
            raise ValueError("LanceDB 搜尋必須提供 embedding 向量")

        table = self.db.open_table(collection_name)

        # 從 table metadata 取得距離度量方式
        meta = self._get_table_metadata(collection_name)
        metric = meta.get("distance_metric", "cosine")

        search_query = (
            table.search(query.embedding, vector_column_name="vector")
            .metric(metric)
            .limit(query.top_k)
        )

        if query.filter:
            # 將 filter dict 轉換為 SQL where 子句
            where_clauses = []
            for key, value in query.filter.items():
                if isinstance(value, str):
                    # 不加尾端引號，支援前綴匹配：
                    # "CMS" 匹配 "CMS-XX"、"CMS-YY" 等
                    where_clauses.append(f'metadata_json LIKE \'%"{key}": "{value}%\'')
            if where_clauses:
                search_query = search_query.where(" AND ".join(where_clauses))

        results = search_query.to_list()

        search_results = []
        for row in results:
            distance = row.get("_distance", 0)
            # 將距離轉換為相似度分數
            if metric == "cosine":
                score = 1 - distance
            elif metric in ("L2", "l2", "euclidean"):
                score = 1 / (1 + distance)
            else:  # dot product
                score = -distance

            metadata = self._parse_metadata_json(row.get("metadata_json"))

            search_results.append(VectorSearchResult(
                id=row["id"],
                score=score,
                embedding=row.get("vector") if query.include_embeddings else None,
                metadata=metadata,
                document=row.get("document"),
            ))

        return search_results

    async def get_distinct_projects(self, collection_name: str) -> List[str]:
        """取得 collection 中所有不重複的 project 名稱"""
        try:
            table = self.db.open_table(collection_name)
            arrow_table = table.to_arrow()
            col = arrow_table.column("metadata_json")
            projects: set[str] = set()
            for raw in col.to_pylist():
                meta = self._parse_metadata_json(raw)
                p = meta.get("project")
                if p:
                    projects.add(p)
            return sorted(projects)
        except Exception:
            return []
