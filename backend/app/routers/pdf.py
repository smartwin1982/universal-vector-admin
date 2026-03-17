"""
PDF 上傳 API 端點
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from app.models.pdf import PDFChunkingConfig, PDFUploadResponse
from app.models.vector import VectorQuery
from app.services.pdf_service import pdf_service
from app.services.embedding_service import embedding_service
from app.services.connection_manager import ConnectionManager

router = APIRouter()
connection_manager = ConnectionManager()

EMBED_BATCH_SIZE = 64


@router.post("/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF 檔案"),
    connection_id: str = Query(..., description="連線 ID"),
    collection_name: str = Query(..., description="Collection 名稱"),
    chunk_size: int = Query(500, ge=50, le=5000, description="每個 chunk 的字元數"),
    chunk_overlap: int = Query(50, ge=0, le=500, description="chunk 之間的重疊字元數"),
):
    """上傳 PDF → 提取文字 → 分塊 → 產生 embedding → 寫入向量 DB"""
    # 驗證檔案類型
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="僅支援 PDF 檔案")

    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="檔案類型必須是 application/pdf")

    # 取得 DB client
    client = connection_manager.get_client(connection_id)
    if not client:
        raise HTTPException(status_code=404, detail="連線不存在或未連線")

    # 重複檢查：查詢是否已有同檔名的 PDF
    try:
        check_query = VectorQuery(
            embedding=embedding_service.embed(file.filename),
            top_k=1,
            filter={"source": file.filename, "type": "pdf"},
        )
        existing = await client.search(collection_name, check_query)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"此 PDF「{file.filename}」已上傳過，請勿重複上傳",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # 查詢失敗不阻擋上傳流程

    try:
        # 讀取 PDF
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="PDF 檔案為空")

        # 解析 + 分塊
        config = PDFChunkingConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks, total_pages = pdf_service.parse_and_chunk(pdf_bytes, file.filename, config)

        if not chunks:
            raise HTTPException(status_code=400, detail="PDF 中未提取到任何文字")

        # 批次 embed + 寫入
        chunks_inserted = 0
        for i in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch_chunks = chunks[i:i + EMBED_BATCH_SIZE]
            texts = [c.text for c in batch_chunks]

            embeddings = embedding_service.embed_batch(texts)
            vectors = pdf_service.chunks_to_vectors(batch_chunks, embeddings)

            count = await client.insert_vectors(collection_name, vectors)
            chunks_inserted += count

        return PDFUploadResponse(
            filename=file.filename,
            total_pages=total_pages,
            total_chunks=len(chunks),
            chunks_inserted=chunks_inserted,
            message=f"成功處理 {file.filename}：{total_pages} 頁、{chunks_inserted} 個分塊已存入",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 處理失敗：{str(e)}")
