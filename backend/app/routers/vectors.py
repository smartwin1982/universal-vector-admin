"""
向量操作路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.models import Vector, VectorCreate, VectorQuery, VectorSearchResult, VectorBatchCreate
from app.services.connection_manager import ConnectionManager
from app.services.embedding_service import embedding_service

router = APIRouter()
connection_manager = ConnectionManager()


@router.get("", response_model=List[Vector])
async def list_vectors(
    connection_id: str = Query(..., description="連線 ID"),
    collection_name: str = Query(..., description="Collection 名稱"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """取得向量列表"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")
        return await client.list_vectors(collection_name, limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=Vector)
async def create_vector(
    vector: VectorCreate,
    connection_id: str = Query(..., description="連線 ID"),
    collection_name: str = Query(..., description="Collection 名稱"),
):
    """新增單一向量（若沒帶 embedding 但有 document，自動產生 embedding）"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")

        if not vector.embedding and vector.document:
            vector.embedding = embedding_service.embed(vector.document)

        return await client.insert_vector(collection_name, vector)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch")
async def create_vectors_batch(
    batch: VectorBatchCreate,
    connection_id: str = Query(..., description="連線 ID"),
    collection_name: str = Query(..., description="Collection 名稱"),
):
    """批次新增向量（若沒帶 embedding 但有 document，自動產生 embedding）"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")

        # 找出需要自動產生 embedding 的向量
        texts_to_embed = []
        indices_to_fill = []
        for i, v in enumerate(batch.vectors):
            if not v.embedding and v.document:
                texts_to_embed.append(v.document)
                indices_to_fill.append(i)

        if texts_to_embed:
            embeddings = embedding_service.embed_batch(texts_to_embed)
            for idx, emb in zip(indices_to_fill, embeddings):
                batch.vectors[idx].embedding = emb

        count = await client.insert_vectors(collection_name, batch.vectors)
        return {"message": f"成功新增 {count} 筆向量", "count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/search", response_model=List[VectorSearchResult])
async def search_vectors(
    query: VectorQuery,
    connection_id: str = Query(..., description="連線 ID"),
    collection_name: str = Query(..., description="Collection 名稱"),
):
    """向量相似度搜尋（若有 query_text，自動轉為 embedding）"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")

        if not query.embedding and query.query_text:
            query.embedding = embedding_service.embed(query.query_text)

        return await client.search(collection_name, query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{vector_id}", response_model=Vector)
async def get_vector(
    vector_id: str,
    connection_id: str = Query(..., description="連線 ID"),
    collection_name: str = Query(..., description="Collection 名稱"),
):
    """取得單一向量"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")
        vector = await client.get_vector(collection_name, vector_id)
        if not vector:
            raise HTTPException(status_code=404, detail="向量不存在")
        return vector
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{vector_id}")
async def delete_vector(
    vector_id: str,
    connection_id: str = Query(..., description="連線 ID"),
    collection_name: str = Query(..., description="Collection 名稱"),
):
    """刪除向量"""
    try:
        client = connection_manager.get_client(connection_id)
        if not client:
            raise HTTPException(status_code=404, detail="連線不存在或未連線")
        await client.delete_vector(collection_name, vector_id)
        return {"message": f"向量 '{vector_id}' 已刪除"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
