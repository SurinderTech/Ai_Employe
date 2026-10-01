"""
AI Business Employee -- FastAPI Application Entry Point
"""
import uvicorn
import time
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging
from app.database.session import init_db
from app.api.v1 import router as api_v1_router

# Force UTF-8 stdout so print() doesn't crash on Windows cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan -- startup and shutdown."""
    from app.core.logging import logger
    from app.core.redis import get_redis, close_redis
    print(f"\n{'='*60}")
    print(f"  [START] {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"  [API]   http://localhost:8000")
    print(f"  [DOCS]  http://localhost:8000/docs")
    print(f"  [AUTH]  http://localhost:8000/api/v1/auth/login")
    print(f"  [CORS]  {settings.CORS_ORIGINS}")
    print(f"{'='*60}\n")
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    await get_redis()   # warm-up Redis (logs warning if down, does NOT crash)
    print("[OK] Backend ready -- waiting for requests...\n")
    yield
    await close_redis()
    logger.info("Shutting down AI Business Employee")
    print("\n[STOP] Backend shutdown complete.\n")


app = FastAPI(
    title="AI Business Employee API",
    description="The complete AI employee backend: calls, leads, CRM, calendar, WhatsApp.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# -- CORS -----------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- Request logger middleware --------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    print(f"  --> {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        status = response.status_code
        tag = "[OK]" if status < 400 else ("[WARN]" if status < 500 else "[ERR]")
        print(f"  {tag} {request.method} {request.url.path} -> {status} ({duration_ms:.0f}ms)")
        return response
    except Exception as exc:
        duration_ms = (time.time() - start) * 1000
        print(f"  [CRASH] {request.method} {request.url.path} -> 500 ({duration_ms:.0f}ms): {exc}")
        return JSONResponse(status_code=500, content={"detail": str(exc)})


# -- Routers --------------------------------------------------------------------
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )