"""
RAG 問答 API 端點
"""
import traceback
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.rag import RAGAskRequest, RAGAskResponse
from app.models.session import ConversationSessionResponse
from app.services.rag_service import rag_service
from app.services.session_service import session_service
from app.services.llm import get_llm_service

router = APIRouter()


@router.post("/ask", response_model=RAGAskResponse)
async def rag_ask(req: RAGAskRequest):
    """RAG 問答：使用者提問 → 向量搜尋 → LLM 回答"""
    try:
        return await rag_service.ask(
            question=req.question,
            connection_id=req.connection_id,
            collection_name=req.collection_name,
            top_k=req.top_k,
            llm_provider=req.llm_provider,
            session_id=req.session_id,
            project=req.project,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"RAG 問答失敗：{str(e)}")


@router.post("/ask/stream")
async def rag_ask_stream(req: RAGAskRequest):
    """RAG 串流問答：使用 SSE 逐步回傳結果"""
    try:
        return StreamingResponse(
            rag_service.ask_stream(
                question=req.question,
                connection_id=req.connection_id,
                collection_name=req.collection_name,
                top_k=req.top_k,
                llm_provider=req.llm_provider,
                session_id=req.session_id,
                project=req.project,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"RAG 串流問答失敗：{str(e)}")


# ========== Session 管理 ==========


@router.post("/sessions")
async def create_session():
    """建立新的對話 session"""
    session = session_service.create_session()
    return {"session_id": session.session_id, "created_at": session.created_at.isoformat()}


@router.get("/sessions/{session_id}", response_model=ConversationSessionResponse)
async def get_session(session_id: str):
    """取得對話歷史"""
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在或已過期")
    return ConversationSessionResponse(
        session_id=session.session_id,
        messages=[
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in session.messages
        ],
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """刪除對話 session"""
    deleted = session_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session 不存在")
    return {"status": "deleted", "session_id": session_id}


@router.get("/health")
async def rag_health():
    """檢查 LLM 服務健康狀態"""
    try:
        llm = get_llm_service()
        is_healthy = await llm.health_check()
        return {
            "status": "ok" if is_healthy else "unavailable",
            "llm_provider": llm.provider_name,
            "healthy": is_healthy,
        }
    except Exception as e:
        return {
            "status": "error",
            "llm_provider": "unknown",
            "healthy": False,
            "detail": str(e),
        }
