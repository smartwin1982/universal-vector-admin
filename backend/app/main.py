"""
Universal Vector Admin - FastAPI Backend
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import connections, collections, vectors, health, rag, pdf, documents, auth

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("uva")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    logger.info(f"Universal Vector Admin v{settings.VERSION} starting...")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Auth enabled: {settings.AUTH_ENABLED}")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Universal Vector Admin",
    description="Universal vector database management platform API",
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS (configured via environment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (optional)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting enabled (100/min)")
except ImportError:
    logger.info("slowapi not installed, rate limiting disabled")

# Register routers
app.include_router(health.router, tags=["Health"])
app.include_router(connections.router, prefix="/api/connections", tags=["Connections"])
app.include_router(collections.router, prefix="/api/collections", tags=["Collections"])
app.include_router(vectors.router, prefix="/api/vectors", tags=["Vectors"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])


@app.get("/")
async def root():
    return {
        "name": "Universal Vector Admin",
        "version": settings.VERSION,
        "docs": "/docs",
    }
