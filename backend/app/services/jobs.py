"""DB-backed async job queue with background worker."""
from __future__ import annotations
from app.models.job import Job, JobQueueStatus, _handlers, register_handler
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

logger = logging.getLogger(__name__)





class JobWorker:
    """Async background worker that polls and executes jobs."""

    def __init__(self, session_factory: Any, poll_interval: float = 2.0) -> None:
        self._session_factory = session_factory
        self._poll_interval = poll_interval
        self._running = False
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="job-worker")
        logger.info("Job worker started")

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Job worker stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._process_one()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Job worker error: %s", exc)
            await asyncio.sleep(self._poll_interval)

    async def _process_one(self) -> None:
        """Pick one pending job and execute it."""
        async with self._session_factory() as db:
            # Atomic claim: select pending, mark running
            result = await db.execute(
                select(Job)
                .where(Job.status == JobQueueStatus.pending)
                .order_by(Job.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            job.status = JobQueueStatus.running
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

            handler = _handlers.get(job.job_type)
            if not handler:
                job.status = JobQueueStatus.failed
                job.error_message = f"No handler registered for job type: {job.job_type}"
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            try:
                import inspect
                payload = job.payload_json or {}
                if len(inspect.signature(handler).parameters) >= 2:
                    result_data = await handler(payload, db)
                else:
                    result_data = await handler(payload)
                job.status = JobQueueStatus.completed
                job.result_json = result_data
                job.completed_at = datetime.now(timezone.utc)
                logger.info("Job %s completed", job.id)
            except Exception as exc:
                job.retry_count += 1
                if job.retry_count >= job.max_retries:
                    job.status = JobQueueStatus.failed
                    job.error_message = str(exc)
                    job.completed_at = datetime.now(timezone.utc)
                    logger.error("Job %s failed permanently: %s", job.id, exc)
                else:
                    job.status = JobQueueStatus.pending
                    job.started_at = None
                    logger.warning("Job %s failed (retry %d/%d): %s", job.id, job.retry_count, job.max_retries, exc)
            await db.commit()


async def enqueue_job(
    db: Any,
    *,
    job_type: str,
    payload: dict[str, Any],
    org_id: uuid.UUID | None = None,
    max_retries: int = 3,
) -> Job:
    """Enqueue a job for async processing."""
    job = Job(
        job_type=job_type,
        payload_json=payload,
        org_id=org_id,
        max_retries=max_retries,
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()
    return job


# ── Registered Default Job Handlers ──────────────────────────────────────────

@register_handler("validate_content")
async def _handle_validate_content(payload: dict[str, Any], db: Any) -> dict[str, Any]:
    from app.services.validation import run_validation_pipeline
    job_id = uuid.UUID(payload["validation_job_id"])
    org_id = uuid.UUID(payload["org_id"])
    return await run_validation_pipeline(db, job_id, org_id)


@register_handler("source_change_impact")
async def _handle_source_change_impact(payload: dict[str, Any], db: Any) -> dict[str, Any]:
    from app.services.continuity import trigger_source_version_change
    from app.models.user import User
    source_id = uuid.UUID(payload["source_id"])
    org_id = uuid.UUID(payload["org_id"])
    actor_id = uuid.UUID(payload["actor_id"])
    user_res = await db.execute(select(User).where(User.id == actor_id))
    user = user_res.scalar_one()
    return await trigger_source_version_change(
        db,
        source_id=source_id,
        org_id=org_id,
        actor=user,
        change_summary=payload.get("change_summary", "Updated source version"),
        new_content_text=payload.get("new_content_text"),
    )


