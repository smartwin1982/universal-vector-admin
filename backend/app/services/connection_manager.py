"""
連線管理器
負責管理所有向量資料庫連線
"""
from typing import Dict, List, Optional
from datetime import datetime
import uuid

from app.models import Connection, ConnectionCreate, ConnectionTest
from app.services.base_client import BaseVectorDBClient
from app.services.clients import ChromaClient, LanceDBClient, QdrantClient, MilvusClient


class ConnectionManager:
    """連線管理器 - 單例模式"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not ConnectionManager._initialized:
            self._connections: Dict[str, Connection] = {}
            self._clients: Dict[str, BaseVectorDBClient] = {}
            ConnectionManager._initialized = True
    
    def _get_client_class(self, db_type: str):
        """根據資料庫類型取得對應的客戶端類"""
        clients = {
            "lancedb": LanceDBClient,
            **({"chroma": ChromaClient} if ChromaClient else {}),
            **({"qdrant": QdrantClient} if QdrantClient else {}),
            **({"milvus": MilvusClient} if MilvusClient else {}),
        }
        return clients.get(db_type)
    
    def list_connections(self) -> List[Connection]:
        """列出所有連線"""
        return list(self._connections.values())
    
    def create_connection(self, conn: ConnectionCreate) -> Connection:
        """建立新連線（只儲存配置，不實際連線）"""
        connection_id = str(uuid.uuid4())
        
        connection = Connection(
            id=connection_id,
            name=conn.name,
            db_type=conn.db_type,
            host=conn.host,
            port=conn.port,
            api_key=conn.api_key,
            extra_config=conn.extra_config,
            is_connected=False,
            created_at=datetime.now(),
        )
        
        self._connections[connection_id] = connection
        return connection
    
    def get_connection(self, connection_id: str) -> Optional[Connection]:
        """取得指定連線"""
        return self._connections.get(connection_id)
    
    def delete_connection(self, connection_id: str) -> bool:
        """刪除連線"""
        if connection_id in self._connections:
            # 先斷開連線
            self.disconnect(connection_id)
            del self._connections[connection_id]
            return True
        return False
    
    async def connect(self, connection_id: str) -> bool:
        """建立實際連線"""
        conn = self._connections.get(connection_id)
        if not conn:
            raise ValueError("連線不存在")
        
        # 取得對應的客戶端類
        client_class = self._get_client_class(conn.db_type)
        if not client_class:
            raise ValueError(f"不支援的資料庫類型: {conn.db_type}")
        
        # 建立客戶端配置
        config = {
            "host": conn.host,
            "port": conn.port,
            "api_key": conn.api_key,
            **(conn.extra_config or {}),
        }
        
        # 建立並連接客戶端
        client = client_class(connection_id, config)
        await client.connect()
        
        # 儲存客戶端實例
        self._clients[connection_id] = client
        
        # 更新連線狀態
        conn.is_connected = True
        conn.updated_at = datetime.now()
        
        return True
    
    def disconnect(self, connection_id: str) -> None:
        """斷開連線"""
        if connection_id in self._clients:
            # 注意：這裡應該是 async，但為了簡化先用同步
            del self._clients[connection_id]
        
        if connection_id in self._connections:
            self._connections[connection_id].is_connected = False
            self._connections[connection_id].updated_at = datetime.now()
    
    def get_client(self, connection_id: str) -> Optional[BaseVectorDBClient]:
        """取得連線的客戶端實例"""
        return self._clients.get(connection_id)
    
    async def test_connection(self, conn: ConnectionTest) -> bool:
        """測試連線（不儲存）"""
        client_class = self._get_client_class(conn.db_type)
        if not client_class:
            raise ValueError(f"不支援的資料庫類型: {conn.db_type}")
        
        config = {
            "host": conn.host,
            "port": conn.port,
            "api_key": conn.api_key,
            **(conn.extra_config or {}),
        }
        
        client = client_class("test", config)
        try:
            await client.connect()
            result = await client.test_connection()
            await client.disconnect()
            return result
        except:
            return False
