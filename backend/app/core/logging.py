"""Structured logging with correlation IDs and sensitive data scrubbing."""
from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for request correlation ID
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="system"
)

SENSITIVE_PATTERNS = [
    re.compile(r"(password|passwd|pwd)\s*[=:]\s*['\"]?([^'\"\s,]+)", re.IGNORECASE),
    re.compile(r"(access_token|refresh_token|token|jwt|secret|key)\s*[=:]\s*['\"]?([^'\"\s,]+)", re.IGNORECASE),
    re.compile(r"(Bearer\s+)([A-Za-z0-9\-_\.]+)", re.IGNORECASE),
]

SENSITIVE_KEYS = {
    "password", "hashed_password", "token", "access_token", "refresh_token",
    "jwt_secret_key", "secret", "gemini_api_key", "authorization", "cookie"
}


def sanitize_value(key: str, value: Any) -> Any:
    """Sanitize sensitive fields and truncate full document bodies."""
    lower_key = key.lower()
    if lower_key in SENSITIVE_KEYS or any(s in lower_key for s in ("password", "secret", "token")):
        return "[REDACTED]"
    
    # Truncate full raw document contents in logs
    if lower_key in ("content_text", "raw_text", "file_content", "document_content"):
        if isinstance(value, str) and len(value) > 100:
            return value[:100] + f"... [truncated {len(value)} chars]"

    if isinstance(value, dict):
        return {k: sanitize_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_value("", v) if not isinstance(v, (str, int, float, bool)) else v for v in value]
    return value


def sanitize_text(text: str) -> str:
    """Scrub tokens and passwords from raw strings."""
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub(r"\1 [REDACTED]", text)
    return text


class StructuredLogFormatter(logging.Formatter):
    """Formats logs as JSON including correlation ID and timestamp."""

    def format(self, record: logging.LogRecord) -> str:
        cid = correlation_id_ctx.get()
        message = sanitize_text(record.getMessage())

        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": cid,
            "message": message,
        }

        if record.exc_info:
            # Format exception without leaking full system path details
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def configure_logging(level: int = logging.INFO) -> None:
    """Setup root logger with JSON formatting."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredLogFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid adding duplicate handlers
    root_logger.handlers = [handler]


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Ensures every request has a correlation ID passed through headers and logs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check incoming header or generate new
        cid = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = correlation_id_ctx.set(cid)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            correlation_id_ctx.reset(token)

