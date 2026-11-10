"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import CorrelationIdMiddleware, configure_logging
from app.db.session import AsyncSessionLocal
from app.services.jobs import JobWorker

configure_logging()
logger = logging.getLogger("bridge.main")

_worker: JobWorker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle."""
    global _worker
    logger.info(
        "BRIDGE API starting up (env=%s, ai=%s, status=%s)",
        settings.environment, settings.ai_provider, settings.ai_status,
    )

    # Start background job worker
    _worker = JobWorker(session_factory=AsyncSessionLocal, poll_interval=2.0)
    _worker.start()

    yield

    # Shutdown
    if _worker:
        _worker.stop()
    logger.info("BRIDGE API shut down cleanly")


app = FastAPI(
    title="BRIDGE API",
    description="Brand Rules, Intelligence, Dependency, Governance & Evidence",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Correlation ID tracing middleware
app.add_middleware(CorrelationIdMiddleware)

# Error handlers
register_error_handlers(app)

# Security Headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
from app.api.v1.router import router as v1_router  # noqa: E402
app.include_router(v1_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {
        "status": "ok",
        "version": "2.0.0",
        "environment": settings.environment,
        "ai_status": settings.ai_status,
    }


@app.get("/ready", tags=["health"])
async def ready() -> dict:
    """Readiness probe checking database connectivity and pgvector extension."""
    from fastapi.responses import JSONResponse
    from sqlalchemy import text

    checks: dict[str, str] = {
        "database": "unknown",
        "pgvector": "unknown",
    }
    is_ready = True

    if settings.demo_mode:
        checks["database"] = "ok (demo_mode)"
        checks["pgvector"] = "ok (demo_mode)"
        return {
            "status": "ok",
            "checks": checks,
            "environment": settings.environment,
            "demo_mode": True,
        }

    try:
        async with AsyncSessionLocal() as session:
            # 1. Check basic DB connectivity
            await session.execute(text("SELECT 1"))
            checks["database"] = "ok"

            # 2. Check pgvector extension
            res = await session.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            has_vector = res.scalar_one_or_none() is not None
            if has_vector:
                checks["pgvector"] = "ok"
            else:
                checks["pgvector"] = "missing"
                is_ready = False
    except Exception as exc:
        checks["database"] = f"unreachable: {str(exc)}"
        checks["pgvector"] = "unknown"
        is_ready = False

    payload = {
        "status": "ok" if is_ready else "error",
        "checks": checks,
        "environment": settings.environment,
        "demo_mode": settings.demo_mode,
    }
    if not is_ready:
        return JSONResponse(status_code=503, content=payload)
    return payload
