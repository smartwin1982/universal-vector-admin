"""
RAG 協調服務
負責串接 embedding → 向量搜尋 → 組 prompt → LLM 生成
"""
import json
from typing import AsyncGenerator, List, Optional

from app.core.config import settings
from app.models.rag import RAGAskResponse, RAGSourceDocument
from app.models.vector import VectorQuery
from app.services.embedding_service import embedding_service
from app.services.connection_manager import ConnectionManager
from app.services.llm import get_llm_service


class RAGService:
    """RAG 問答服務"""

    def __init__(self):
        self._connection_manager = ConnectionManager()

    def _get_client(self, connection_id: str):
        client = self._connection_manager.get_client(connection_id)
        if not client:
            raise ValueError("連線不存在或尚未連線，請先建立連線")
        return client

    @staticmethod
    def _match_project(question: str, projects: List[str]) -> str | None:
        """從問題中自動偵測專案名稱。
        按名稱長度由長到短匹配（優先匹配最具體的）。
        """
        if not projects:
            return None
        for p in sorted(projects, key=len, reverse=True):
            if p in question:
                return p
        return None

    async def _retrieve_sources(
        self,
        question: str,
        connection_id: str,
        collection_name: str,
        top_k: int = 5,
        project: str | None = None,
    ) -> tuple[List[RAGSourceDocument], str, str | None, List[str]]:
        """檢索相關文件，回傳 (sources, context_text, detected_project, all_projects)"""
        query_embedding = embedding_service.embed(question)
        client = self._get_client(connection_id)

        # 取得所有專案清單
        all_projects = await client.get_distinct_projects(collection_name)

        # 未手動指定 project 時，自動從問題偵測
        detected_project = None
        if not project:
            detected_project = self._match_project(question, all_projects)
            project = detected_project

        query_filter = {"project": project} if project else None
        query = VectorQuery(embedding=query_embedding, top_k=top_k, filter=query_filter)
        results = await client.search(
            collection_name=collection_name,
            query=query,
        )

        sources: List[RAGSourceDocument] = []
        context_parts: List[str] = []

        for i, r in enumerate(results, 1):
            doc_text = r.document or ""
            if doc_text:
                proj_label = ""
                if r.metadata and r.metadata.get("project"):
                    proj_label = f"（專案：{r.metadata['project']}）"
                context_parts.append(f"[文件 {i}]{proj_label} {doc_text}")
                sources.append(RAGSourceDocument(
                    id=r.id,
                    document=doc_text,
                    score=r.score,
                ))

        context = "\n\n".join(context_parts) if context_parts else "（未找到相關文件）"
        return sources, context, detected_project, all_projects

    def _build_user_prompt(
        self,
        question: str,
        context: str,
        conversation_history: Optional[str] = None,
        all_projects: Optional[List[str]] = None,
    ) -> str:
        parts = []
        if all_projects:
            parts.append(f"資料庫中目前有以下專案：{', '.join(all_projects)}\n")
        if conversation_history:
            parts.append(f"以下是先前的對話記錄：\n{conversation_history}\n")
        parts.append(
            f"以下是檢索到的相關文件：\n\n{context}\n\n"
            f"使用者的問題：{question}\n\n"
            f"請根據上述文件內容回答問題。如果文件中沒有相關資訊，請誠實說明。"
        )
        return "\n".join(parts)

    async def ask(
        self,
        question: str,
        connection_id: str,
        collection_name: str,
        top_k: int = 5,
        llm_provider: str | None = None,
        session_id: str | None = None,
        project: str | None = None,
    ) -> RAGAskResponse:
        """完整 RAG 流程（非串流）"""
        sources, context, _, all_projects = await self._retrieve_sources(
            question, connection_id, collection_name, top_k, project=project
        )

        # 對話記憶
        conversation_history = None
        if session_id:
            from app.services.session_service import session_service
            session = session_service.get_session(session_id)
            if session and session.messages:
                conversation_history = "\n".join(
                    f"{m.role}: {m.content}" for m in session.messages
                )

        user_prompt = self._build_user_prompt(question, context, conversation_history, all_projects)

        llm = get_llm_service(llm_provider)
        answer = await llm.generate(
            prompt=user_prompt,
            system_prompt=settings.RAG_SYSTEM_PROMPT,
        )

        # 儲存到 session
        if session_id:
            from app.services.session_service import session_service
            session_service.add_message(session_id, "user", question)
            session_service.add_message(session_id, "assistant", answer)

        return RAGAskResponse(
            answer=answer,
            sources=sources,
            llm_provider=llm.provider_name,
        )

    async def ask_stream(
        self,
        question: str,
        connection_id: str,
        collection_name: str,
        top_k: int = 5,
        llm_provider: str | None = None,
        session_id: str | None = None,
        project: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        串流 RAG 流程，yield SSE 格式事件：
        - event: sources  data: [...]
        - event: chunk    data: "text"
        - event: done     data: {}
        """
        sources, context, detected_project, all_projects = await self._retrieve_sources(
            question, connection_id, collection_name, top_k, project=project
        )

        # 先送出 sources（含自動偵測到的專案名）
        sources_data = [s.model_dump() for s in sources]
        yield f"event: sources\ndata: {json.dumps(sources_data, ensure_ascii=False)}\n\n"

        # 通知前端自動偵測到的專案
        if detected_project:
            yield f"event: auto_project\ndata: {json.dumps(detected_project, ensure_ascii=False)}\n\n"

        # 對話記憶
        conversation_history = None
        if session_id:
            from app.services.session_service import session_service
            session = session_service.get_session(session_id)
            if session and session.messages:
                conversation_history = "\n".join(
                    f"{m.role}: {m.content}" for m in session.messages
                )

        user_prompt = self._build_user_prompt(question, context, conversation_history, all_projects)

        llm = get_llm_service(llm_provider)
        full_answer = ""

        async for chunk in llm.stream_generate(
            prompt=user_prompt,
            system_prompt=settings.RAG_SYSTEM_PROMPT,
        ):
            full_answer += chunk
            yield f"event: chunk\ndata: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        # 儲存到 session
        if session_id:
            from app.services.session_service import session_service
            session_service.add_message(session_id, "user", question)
            session_service.add_message(session_id, "assistant", full_answer)

        yield f"event: done\ndata: {json.dumps({'llm_provider': llm.provider_name})}\n\n"


rag_service = RAGService()
