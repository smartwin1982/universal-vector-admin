"""
認證 API 端點
"""
from fastapi import APIRouter, HTTPException, Depends

from app.core.config import settings
from app.core.security import create_access_token, get_current_user
from app.models.user import UserCreate, UserLogin, Token, UserInfo
from app.services.user_service import user_service

router = APIRouter()


@router.post("/register", response_model=Token)
async def register(req: UserCreate):
    """註冊新使用者"""
    if not settings.AUTH_ENABLED:
        raise HTTPException(status_code=400, detail="Authentication is disabled")

    try:
        user = user_service.create_user(req.username, req.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    token = create_access_token(data={"sub": user.username})
    return Token(access_token=token, username=user.username)


@router.post("/login", response_model=Token)
async def login(req: UserLogin):
    """使用者登入"""
    if not settings.AUTH_ENABLED:
        raise HTTPException(status_code=400, detail="Authentication is disabled")

    user = user_service.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(data={"sub": user.username})
    return Token(access_token=token, username=user.username)


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: dict = Depends(get_current_user)):
    """取得當前使用者資訊"""
    if current_user is None:
        return UserInfo(username="anonymous", created_at="N/A")
    return UserInfo(**current_user)
