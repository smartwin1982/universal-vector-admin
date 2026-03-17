"""
JWT 認證與密碼 hash 工具
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

security_scheme = HTTPBearer(auto_error=False)

# Lazy imports to avoid requiring dependencies when auth is disabled
_jwt_module = None
_pwd_context = None


def _ensure_jwt():
    global _jwt_module
    if _jwt_module is None:
        try:
            from jose import jwt
            _jwt_module = jwt
        except ImportError:
            raise ImportError("python-jose[cryptography] is required: pip install python-jose[cryptography]")
    return _jwt_module


def _ensure_pwd():
    global _pwd_context
    if _pwd_context is None:
        try:
            from passlib.context import CryptContext
            _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        except ImportError:
            raise ImportError("passlib[bcrypt] is required: pip install passlib[bcrypt]")
    return _pwd_context


def hash_password(password: str) -> str:
    """Hash a password"""
    pwd = _ensure_pwd()
    return pwd.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    pwd = _ensure_pwd()
    return pwd.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    jwt = _ensure_jwt()
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode a JWT access token"""
    jwt = _ensure_jwt()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[dict]:
    """
    Get current user from JWT token.
    Returns None if auth is disabled or no token provided.
    """
    if not settings.AUTH_ENABLED:
        return None

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = decode_access_token(credentials.credentials)
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    from app.services.user_service import user_service
    user = user_service.get_user(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return {"username": user.username, "created_at": user.created_at.isoformat()}
