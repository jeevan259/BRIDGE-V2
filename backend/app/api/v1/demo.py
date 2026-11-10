"""Demo seeding endpoint.

POST /demo/seed — seeds the Aurora Outdoors demo tenant.
Only accessible when DEMO_MODE=true and the caller is an administrator.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text

from app.api.deps import DbDep, require_role
from app.core.config import settings
from app.models.audit import AuditEvent
from app.models.user import User, UserRole
from app.seed_demo import seed_demo_tenant
from app.services.audit import append_audit_event

router = APIRouter(prefix="/demo", tags=["demo"])

_TAMPER_BACKUPS: dict[uuid.UUID, dict[str, Any]] = {}


@router.post("/seed", status_code=status.HTTP_200_OK)
async def seed_demo(
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator)),
    reset: bool = Query(False, description="If true, purge existing demo data before seeding"),
) -> dict:
    """Seed the demo tenant (idempotent).

    - Requires DEMO_MODE=true in env.
    - Only administrators can invoke.
    """
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode disabled",
        )

    result = await seed_demo_tenant(db, reset=reset)

    await append_audit_event(
        db,
        org_id=current_user.org_id,
        event_type="DEMO_SEED_EXECUTED",
        actor=current_user,
        resource_type="demo",
        resource_id="seed",
        diff_json={"reset": reset, "status": result.get("status")},
    )
    return result


@router.post("/tamper", status_code=status.HTTP_200_OK)
async def tamper_audit_log(
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator)),
) -> dict:
    """Simulate an attacker mutating an audit event behind the scenes.

    Bypasses the append-only trigger within a transaction, never weakening the trigger permanently.
    Only available when DEMO_MODE=true and caller is an administrator.
    """
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode disabled",
        )

    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.org_id == current_user.org_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(1)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="No audit events found to tamper with")

    _TAMPER_BACKUPS[current_user.org_id] = {
        "event_id": event.id,
        "original_outcome": event.outcome,
        "original_diff_json": event.diff_json,
    }

    try:
        await db.execute(text("ALTER TABLE audit_events DISABLE TRIGGER trg_block_audit_mutation"))
        event.outcome = "tampered_unauthorized_override"
        await db.flush()
    finally:
        await db.execute(text("ALTER TABLE audit_events ENABLE TRIGGER trg_block_audit_mutation"))

    await db.commit()

    return {
        "status": "tampered",
        "tampered_event_id": str(event.id),
        "message": "Simulated attacker altered audit record payload without updating cryptographic hash chain.",
    }


@router.post("/untamper", status_code=status.HTTP_200_OK)
async def untamper_audit_log(
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator)),
) -> dict:
    """Restore the tampered audit event to its valid state."""
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode disabled",
        )

    backup = _TAMPER_BACKUPS.get(current_user.org_id)
    if not backup:
        result = await db.execute(
            select(AuditEvent)
            .where(AuditEvent.org_id == current_user.org_id, AuditEvent.outcome == "tampered_unauthorized_override")
        )
        tampered_events = result.scalars().all()
        if not tampered_events:
            return {"status": "unchanged", "message": "No tampered records found"}
        events_to_restore = [(e, "success") for e in tampered_events]
    else:
        result = await db.execute(
            select(AuditEvent).where(AuditEvent.id == backup["event_id"])
        )
        event = result.scalar_one_or_none()
        events_to_restore = [(event, backup["original_outcome"])] if event else []

    try:
        await db.execute(text("ALTER TABLE audit_events DISABLE TRIGGER trg_block_audit_mutation"))
        for ev, orig_outcome in events_to_restore:
            if ev:
                ev.outcome = orig_outcome
        await db.flush()
    finally:
        await db.execute(text("ALTER TABLE audit_events ENABLE TRIGGER trg_block_audit_mutation"))

    await db.commit()
    _TAMPER_BACKUPS.pop(current_user.org_id, None)

    return {
        "status": "restored",
        "message": "Tampered records restored. Audit hash chain is intact.",
    }
