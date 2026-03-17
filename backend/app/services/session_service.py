"""
對話 Session 管理服務
In-memory store，含 TTL 自動清理
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.models.session import ConversationMessage, ConversationSession

# 預設 session TTL：1 小時
SESSION_TTL_SECONDS = 3600


class SessionService:
    """對話 Session 管理（Singleton）"""

    _instance: "SessionService | None" = None
    _sessions: Dict[str, ConversationSession]

    def __new__(cls) -> "SessionService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sessions = {}
        return cls._instance

    def _cleanup_expired(self) -> None:
        """清理過期的 session"""
        now = datetime.now()
        expired = [
            sid for sid, session in self._sessions.items()
            if (now - session.updated_at) > timedelta(seconds=SESSION_TTL_SECONDS)
        ]
        for sid in expired:
            del self._sessions[sid]

    def create_session(self) -> ConversationSession:
        """建立新的對話 session"""
        self._cleanup_expired()
        session = ConversationSession(session_id=str(uuid.uuid4()))
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """取得 session（若已過期則回傳 None）"""
        self._cleanup_expired()
        return self._sessions.get(session_id)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """新增訊息到 session"""
        session = self._sessions.get(session_id)
        if not session:
            return
        session.messages.append(ConversationMessage(role=role, content=content))
        session.updated_at = datetime.now()

    def delete_session(self, session_id: str) -> bool:
        """刪除 session，回傳是否成功"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[ConversationSession]:
        """列出所有活躍的 session"""
        self._cleanup_expired()
        return list(self._sessions.values())


session_service = SessionService()
