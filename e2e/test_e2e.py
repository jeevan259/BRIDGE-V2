"""End-to-End integration tests for BRIDGE governance flow."""
from __future__ import annotations

import asyncio
import uuid
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.errors import http_exception_handler
from app.core.logging import CorrelationIdMiddleware, correlation_id_ctx
from app.main import app, health, ready
from app.models.user import UserRole


def test_health_check_returns_ai_status():
    """Verify health check returns version and AI offline/online status without crashing."""
    async def _run():
        data = await health()
        assert data["status"] == "ok"
        assert data["version"] == "2.0.0"
        assert "ai_status" in data
        assert "AI:" in data["ai_status"]

    asyncio.run(_run())


def test_ready_check_returns_db_and_vector_status():
    """Verify readiness check inspects db and pgvector without crashing."""
    async def _run():
        prev_demo = settings.demo_mode
        object.__setattr__(settings, "demo_mode", True)
        try:
            res = await ready()
            if hasattr(res, "body"):
                import json
                data = json.loads(res.body.decode("utf-8"))
            else:
                data = res
            assert data["status"] == "ok"
            assert "checks" in data
            assert "database" in data["checks"]
            assert "pgvector" in data["checks"]
        finally:
            object.__setattr__(settings, "demo_mode", prev_demo)

    asyncio.run(_run())


def test_correlation_id_propagated_in_headers():
    """Verify X-Correlation-ID is set and handled properly in middleware."""
    async def _run():
        custom_cid = f"test-trace-{uuid.uuid4().hex[:8]}"
        middleware = CorrelationIdMiddleware(app=None)

        # Build dummy request
        scope = {
            "type": "http",
            "headers": [(b"x-correlation-id", custom_cid.encode("utf-8"))],
        }
        req = Request(scope)

        async def dummy_call_next(request: Request) -> Response:
            # Check context var has captured incoming correlation ID
            assert correlation_id_ctx.get() == custom_cid
            return Response("OK")

        response = await middleware.dispatch(req, dummy_call_next)
        assert response.headers.get("X-Correlation-ID") == custom_cid

    asyncio.run(_run())


def test_unauthenticated_request_rejected_with_uniform_error():
    """Verify unauthorized access returns user-safe standardized error structure."""
    async def _run():
        # Calling get_current_user without credentials raises 401 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(db=None, credentials=None)

        assert exc_info.value.status_code == 401

        # Pass through custom http_exception_handler to verify user-safe error envelope
        scope = {"type": "http", "method": "GET", "path": "/api/v1/auth/me", "headers": []}
        req = Request(scope)
        res = await http_exception_handler(req, exc_info.value)
        import json
        body = json.loads(res.body.decode("utf-8"))
        assert "error" in body
        assert body["error"]["code"] == "HTTP_401"
        assert "correlation_id" in body["error"]
        assert "detail" not in body  # Sensitive details sanitized

    asyncio.run(_run())
