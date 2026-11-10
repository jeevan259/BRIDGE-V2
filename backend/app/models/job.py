"""Job domain model for background asynchronous processing."""
from __future__ import annotations
import asyncio
import enum
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, select, update
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin
__all__ = ["Job", "JobQueueStatus", "register_handler", "_handlers"]
class JobQueueStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class Job(UUIDMixin, Base):
    """Background job queue table."""
    __tablename__ = "jobs"

    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[JobQueueStatus] = mapped_column(
        Enum(JobQueueStatus, name="job_queue_status"),
        nullable=False,
        default=JobQueueStatus.pending,
        index=True,
    )
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Registry of job handlers: job_type -> async callable
_handlers: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {}


def register_handler(job_type: str) -> Callable:
    """Decorator to register a job handler function."""
    def decorator(fn: Callable) -> Callable:
        _handlers[job_type] = fn
        return fn
    return decorator
