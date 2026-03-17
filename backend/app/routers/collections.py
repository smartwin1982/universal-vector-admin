"""
Collection 管理路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models import Collection, CollectionCreate, CollectionStats
from app.services.connection_manager import ConnectionManager

router = APIRouter()
connection_manager = ConnectionManager()


@router.get("", response_model=List[Collection])
async def list_collections(
    connection_id: str = Query(..., description="連線 ID")
):
    """取得指定連線的所有 Collections"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")
        return await client.list_collections()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=Collection)
async def create_collection(
    collection: CollectionCreate,
    connection_id: str = Query(..., description="連線 ID")
):
    """建立新 Collection"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")
        return await client.create_collection(collection)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{collection_name}", response_model=Collection)
async def get_collection(
    collection_name: str,
    connection_id: str = Query(..., description="連線 ID")
):
    """取得指定 Collection"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")
        collection = await client.get_collection(collection_name)
        if not collection:
            raise HTTPException(status_code=404, detail="Collection 不存在")
        return collection
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{collection_name}")
async def delete_collection(
    collection_name: str,
    connection_id: str = Query(..., description="連線 ID")
):
    """刪除 Collection"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")
        await client.delete_collection(collection_name)
        return {"message": f"Collection '{collection_name}' 已刪除"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{collection_name}/stats", response_model=CollectionStats)
async def get_collection_stats(
    collection_name: str,
    connection_id: str = Query(..., description="連線 ID")
):
    """取得 Collection 統計資訊"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")
        return await client.get_collection_stats(collection_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
