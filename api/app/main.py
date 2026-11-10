"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
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
