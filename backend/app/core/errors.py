"""User-safe exception handlers preventing stack traces from leaking."""
from __future__ import annotations

import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import correlation_id_ctx

logger = logging.getLogger("bridge.errors")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    cid = correlation_id_ctx.get()
    logger.warning(
        "HTTP %s on %s %s: %s (cid=%s)",
        exc.status_code, getattr(request, "method", "GET"), getattr(request.url, "path", ""), exc.detail, cid
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "correlation_id": cid,
            }
        },
        headers={"X-Correlation-ID": cid},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    cid = correlation_id_ctx.get()
    errors = [
        {"loc": ".".join(str(l) for l in err["loc"]), "msg": err["msg"], "type": err["type"]}
        for err in exc.errors()
    ]
    logger.info("Validation error on %s %s (cid=%s): %s", getattr(request, "method", "POST"), getattr(request.url, "path", ""), cid, errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": errors,
                "correlation_id": cid,
            }
        },
        headers={"X-Correlation-ID": cid},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    cid = correlation_id_ctx.get()
    logger.error(
        "Unhandled exception on %s %s (cid=%s): %s",
        getattr(request, "method", "UNKNOWN"), getattr(request.url, "path", ""), cid, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact system administrator with correlation ID.",
                "correlation_id": cid,
            }
        },
        headers={"X-Correlation-ID": cid},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register uniform error response handlers on FastAPI app."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
