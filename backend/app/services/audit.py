"""Audit service — append-only, hash-chained audit log."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.user import User


def _canonical_serialize(event_data: dict[str, Any]) -> str:
    """Produce a deterministic JSON string for hashing."""
    return json.dumps(event_data, sort_keys=True, default=str)


def _compute_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


async def _get_latest_event_hash(db: AsyncSession, org_id: uuid.UUID) -> str | None:
    result = await db.execute(
        select(AuditEvent.event_hash)
        .where(AuditEvent.org_id == org_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row


def _build_hash_payload(
    *,
    event_id: uuid.UUID,
    org_id: uuid.UUID,
    event_type: str,
    actor_id: uuid.UUID | None,
    actor_email: str,
    resource_type: str | None,
    resource_id: str | None,
    diff_json: dict[str, Any] | None,
    outcome: str,
    correlation_id: str | None,
    prev_hash: str | None,
    created_at: datetime,
) -> dict[str, Any]:
    """Build the canonical payload dict used for hashing."""
    return {
        "id": str(event_id),
        "org_id": str(org_id),
        "event_type": event_type,
        "actor_id": str(actor_id) if actor_id else None,
        "actor_email": actor_email,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "diff_json": diff_json,
        "outcome": outcome,
        "correlation_id": correlation_id,
        "prev_hash": prev_hash,
        "created_at": created_at.isoformat(),
    }


async def append_audit_event(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    event_type: str,
    actor: User | None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    diff_json: dict[str, Any] | None = None,
    outcome: str = "success",
    correlation_id: str | None = None,
) -> AuditEvent:
    """Append an audit event with hash chain linking."""
    prev_hash = await _get_latest_event_hash(db, org_id)
    now = datetime.now(timezone.utc)
    event_id = uuid.uuid4()

    actor_id = actor.id if actor else None
    actor_email = actor.email if actor else "system"

    # Compute event hash over canonical payload
    payload = _build_hash_payload(
        event_id=event_id,
        org_id=org_id,
        event_type=event_type,
        actor_id=actor_id,
        actor_email=actor_email,
        resource_type=resource_type,
        resource_id=resource_id,
        diff_json=diff_json,
        outcome=outcome,
        correlation_id=correlation_id,
        prev_hash=prev_hash,
        created_at=now,
    )
    event_hash = _compute_hash(_canonical_serialize(payload))

    event = AuditEvent(
        id=event_id,
        org_id=org_id,
        event_type=event_type,
        actor_id=actor_id,
        actor_email=actor_email,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        diff_json=diff_json,
        outcome=outcome,
        correlation_id=correlation_id,
        prev_hash=prev_hash,
        event_hash=event_hash,
        created_at=now,
    )
    db.add(event)
    await db.flush()
    return event


async def verify_audit_chain(db: AsyncSession, org_id: uuid.UUID) -> dict[str, Any]:
    """Verify the integrity of the audit chain for an org.

    Returns the first broken link or confirms chain integrity.
    """
    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.org_id == org_id)
        .order_by(AuditEvent.created_at.asc())
    )
    events = result.scalars().all()

    if not events:
        return {"is_valid": True, "total_events": 0, "broken_at": None, "message": "No events"}

    prev_hash: str | None = None
    for event in events:
        payload = _build_hash_payload(
            event_id=event.id,
            org_id=event.org_id,
            event_type=event.event_type,
            actor_id=event.actor_id,
            actor_email=event.actor_email,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            diff_json=event.diff_json,
            outcome=event.outcome,
            correlation_id=event.correlation_id,
            prev_hash=prev_hash,
            created_at=event.created_at,
        )
        expected_hash = _compute_hash(_canonical_serialize(payload))
        if expected_hash != event.event_hash:
            return {
                "is_valid": False,
                "total_events": len(events),
                "broken_at": event.id,
                "message": f"Hash mismatch at event {event.id}",
            }
        if event.prev_hash != prev_hash:
            return {
                "is_valid": False,
                "total_events": len(events),
                "broken_at": event.id,
                "message": f"Chain broken at event {event.id}",
            }
        prev_hash = event.event_hash

    return {
        "is_valid": True,
        "total_events": len(events),
        "broken_at": None,
        "message": "Chain intact",
    }
