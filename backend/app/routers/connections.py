"""
連線管理路由
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.models import Connection, ConnectionCreate, ConnectionTest
from app.services.connection_manager import ConnectionManager

router = APIRouter()

# 連線管理器（簡易版本，後續可改用依賴注入）
connection_manager = ConnectionManager()


@router.get("", response_model=List[Connection])
async def list_connections():
    """取得所有連線"""
    return connection_manager.list_connections()


@router.post("", response_model=Connection)
async def create_connection(conn: ConnectionCreate):
    """建立新連線"""
    return connection_manager.create_connection(conn)


@router.get("/{connection_id}", response_model=Connection)
async def get_connection(connection_id: str):
    """取得指定連線"""
    conn = connection_manager.get_connection(connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="連線不存在")
    return conn


@router.delete("/{connection_id}")
async def delete_connection(connection_id: str):
    """刪除連線"""
    success = connection_manager.delete_connection(connection_id)
    if not success:
        raise HTTPException(status_code=404, detail="連線不存在")
    return {"message": "連線已刪除"}


@router.post("/{connection_id}/connect")
async def connect(connection_id: str):
    """建立連線"""
    try:
        result = await connection_manager.connect(connection_id)
        return {"message": "連線成功", "connected": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{connection_id}/disconnect")
async def disconnect(connection_id: str):
    """斷開連線"""
    connection_manager.disconnect(connection_id)
    return {"message": "已斷開連線"}


@router.post("/test")
async def test_connection(conn: ConnectionTest):
    """測試連線（不儲存）"""
    try:
        result = await connection_manager.test_connection(conn)
        return {"success": result, "message": "連線測試成功" if result else "連線測試失敗"}
    except Exception as e:
        return {"success": False, "message": str(e)}
