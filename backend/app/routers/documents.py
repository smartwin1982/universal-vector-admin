"""
統一文件上傳 API 端點 — 支援多種格式
"""
import traceback
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse

from app.models.document import (
    ChunkingStrategy,
    DocumentChunk,
    DocumentUploadResponse,
    WebScrapeRequest,
    BatchScanRequest,
    BatchScanResponse,
    BatchImportRequest,
)
from app.models.vector import VectorCreate
from app.services.document_processors import get_processor, get_supported_extensions
from app.services.chunking import get_chunker
from app.services.embedding_service import embedding_service
from app.services.connection_manager import ConnectionManager
from app.services.batch_import_service import BatchImportService

router = APIRouter()
connection_manager = ConnectionManager()
batch_import_service = BatchImportService()

EMBED_BATCH_SIZE = 64


@router.get("/supported-formats")
async def supported_formats():
    """回傳支援的文件格式"""
    return {"formats": get_supported_extensions()}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="文件檔案"),
    connection_id: str = Query(..., description="連線 ID"),
    collection_name: str = Query(..., description="Collection 名稱"),
    chunk_size: int = Query(500, ge=50, le=5000, description="每個 chunk 的字元數"),
    chunk_overlap: int = Query(50, ge=0, le=500, description="chunk 之間的重疊字元數"),
    strategy: ChunkingStrategy = Query(ChunkingStrategy.recursive, description="分塊策略"),
    project: Optional[str] = Query(None, description="專案名稱"),
):
    """上傳文件 → 提取文字 → 分塊 → 產生 embedding → 寫入向量 DB"""
    filename = file.filename or "unknown"

    # 取得處理器
    processor = get_processor(filename)
    if not processor:
        supported = get_supported_extensions()
        raise HTTPException(
            status_code=400,
            detail=f"不支援此文件格式。支援: {', '.join(supported)}",
        )

    # 取得 DB client
    client = connection_manager.get_client(connection_id)
    if not client:
        raise HTTPException(status_code=404, detail="連線不存在或未連線")

    try:
        # 讀取文件
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="文件為空")

        # 提取文字
        doc = processor.extract_text(file_bytes, filename)
        if not doc.text_pages:
            raise HTTPException(status_code=400, detail="文件中未提取到任何文字")

        # 取得分塊器
        chunker = get_chunker(strategy.value)

        # 分塊
        all_chunks: list[DocumentChunk] = []
        chunk_index = 0
        for page in doc.text_pages:
            text_chunks = chunker.chunk(page.text, chunk_size, chunk_overlap)
            for text in text_chunks:
                all_chunks.append(DocumentChunk(
                    text=text,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    source_filename=filename,
                ))
                chunk_index += 1

        if not all_chunks:
            raise HTTPException(status_code=400, detail="分塊後無有效內容")

        # 批次 embed + 寫入
        file_type = doc.metadata.get("type", "unknown")
        chunks_inserted = 0

        for i in range(0, len(all_chunks), EMBED_BATCH_SIZE):
            batch = all_chunks[i : i + EMBED_BATCH_SIZE]
            texts = [c.text for c in batch]
            embeddings = embedding_service.embed_batch(texts)

            vectors = [
                VectorCreate(
                    document=chunk.text,
                    embedding=emb,
                    metadata={
                        "source": chunk.source_filename,
                        "page": chunk.page_number,
                        "chunk_index": chunk.chunk_index,
                        "type": file_type,
                        **({"project": project} if project else {}),
                    },
                )
                for chunk, emb in zip(batch, embeddings)
            ]

            count = await client.insert_vectors(collection_name, vectors)
            chunks_inserted += count

        return DocumentUploadResponse(
            filename=filename,
            file_type=file_type,
            total_pages=len(doc.text_pages),
            total_chunks=len(all_chunks),
            chunks_inserted=chunks_inserted,
            chunking_strategy=strategy.value,
            message=f"成功處理 {filename}：{len(doc.text_pages)} 頁、{chunks_inserted} 個分塊已存入",
        )

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"文件處理失敗：{str(e)}")


@router.post("/scrape", response_model=DocumentUploadResponse)
async def scrape_web(req: WebScrapeRequest):
    """從 URL 擷取網頁 → 分塊 → 產生 embedding → 寫入向量 DB"""
    client = connection_manager.get_client(req.connection_id)
    if not client:
        raise HTTPException(status_code=404, detail="連線不存在或未連線")

    try:
        # 擷取網頁
        from app.services.document_processors.web_processor import WebProcessor
        web_processor = WebProcessor()
        doc = await web_processor.fetch_and_extract(req.url)

        if not doc.text_pages:
            raise HTTPException(status_code=400, detail="網頁中未提取到任何文字")

        # 分塊
        chunker = get_chunker(req.strategy.value)
        all_chunks: list[DocumentChunk] = []
        chunk_index = 0

        for page in doc.text_pages:
            text_chunks = chunker.chunk(page.text, req.chunk_size, req.chunk_overlap)
            for text in text_chunks:
                all_chunks.append(DocumentChunk(
                    text=text,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    source_filename=req.url,
                ))
                chunk_index += 1

        if not all_chunks:
            raise HTTPException(status_code=400, detail="分塊後無有效內容")

        # 批次 embed + 寫入
        title = doc.metadata.get("title", "")
        chunks_inserted = 0

        for i in range(0, len(all_chunks), EMBED_BATCH_SIZE):
            batch = all_chunks[i : i + EMBED_BATCH_SIZE]
            texts = [c.text for c in batch]
            embeddings = embedding_service.embed_batch(texts)

            vectors = [
                VectorCreate(
                    document=chunk.text,
                    embedding=emb,
                    metadata={
                        "source": req.url,
                        "page": chunk.page_number,
                        "chunk_index": chunk.chunk_index,
                        "type": "web",
                        "title": title,
                        **({"project": req.project} if req.project else {}),
                    },
                )
                for chunk, emb in zip(batch, embeddings)
            ]

            count = await client.insert_vectors(req.collection_name, vectors)
            chunks_inserted += count

        return DocumentUploadResponse(
            filename=req.url,
            file_type="web",
            total_pages=len(doc.text_pages),
            total_chunks=len(all_chunks),
            chunks_inserted=chunks_inserted,
            chunking_strategy=req.strategy.value,
            message=f"成功擷取 {req.url}：{chunks_inserted} 個分塊已存入",
        )

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"網頁擷取失敗：{str(e)}")


# ========== 批次目錄匯入 ==========


@router.post("/batch/scan", response_model=BatchScanResponse)
async def batch_scan(req: BatchScanRequest):
    """掃描伺服器端目錄，回傳支援格式的檔案清單"""
    client = connection_manager.get_client(req.connection_id)
    if not client:
        raise HTTPException(status_code=404, detail="連線不存在或未連線")

    try:
        return batch_import_service.scan_directory(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"掃描失敗：{str(e)}")


@router.post("/batch/import")
async def batch_import(req: BatchImportRequest):
    """批次匯入目錄中的檔案，透過 SSE 串流回報進度"""
    client = connection_manager.get_client(req.connection_id)
    if not client:
        raise HTTPException(status_code=404, detail="連線不存在或未連線")

    return StreamingResponse(
        batch_import_service.import_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
