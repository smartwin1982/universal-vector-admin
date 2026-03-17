"""
使用者管理服務（In-memory store）
"""
from typing import Dict, Optional

from app.models.user import User
from app.core.security import hash_password, verify_password


class UserService:
    """使用者管理服務（Singleton）"""

    _instance: "UserService | None" = None
    _users: Dict[str, User]

    def __new__(cls) -> "UserService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._users = {}
        return cls._instance

    def create_user(self, username: str, password: str) -> User:
        """建立新使用者"""
        if username in self._users:
            raise ValueError(f"Username '{username}' already exists")

        user = User(
            username=username,
            hashed_password=hash_password(password),
        )
        self._users[username] = user
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """驗證使用者，成功回傳 User，失敗回傳 None"""
        user = self._users.get(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def get_user(self, username: str) -> Optional[User]:
        """取得使用者"""
        return self._users.get(username)


user_service = UserService()
