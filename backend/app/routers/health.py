"""
健康檢查路由
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/ready")
async def readiness_check():
    """就緒檢查端點"""
    return {
        "status": "ready",
        "services": {
            "api": True,
        }
    }
