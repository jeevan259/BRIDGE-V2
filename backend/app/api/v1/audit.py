"""Audit log endpoints — read-only, verify chain."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep, require_role
from app.models.audit import AuditEvent
from app.models.user import User, UserRole
from app.schemas.audit import AuditEventList, AuditEventResponse, AuditVerifyResponse
from app.services.audit import verify_audit_chain

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events", response_model=AuditEventList)
async def list_audit_events(
    db: DbDep,
    current_user: User = Depends(require_role(
        UserRole.administrator, UserRole.brand_manager, UserRole.reviewer, UserRole.auditor
    )),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None),
) -> AuditEventList:
    org_id = current_user.org_id
    base = select(AuditEvent).where(AuditEvent.org_id == org_id)
    count_base = select(func.count()).select_from(AuditEvent).where(AuditEvent.org_id == org_id)
    if event_type:
        base = base.where(AuditEvent.event_type == event_type)
        count_base = count_base.where(AuditEvent.event_type == event_type)

    total = (await db.execute(count_base)).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(AuditEvent.created_at.desc()).offset(offset).limit(page_size)
    )
    events = result.scalars().all()
    return AuditEventList(
        items=[AuditEventResponse.model_validate(e) for e in events],
        total=total, page=page, page_size=page_size,
    )


@router.get("/verify", response_model=AuditVerifyResponse)
async def verify_chain(
    db: DbDep,
    current_user: User = Depends(require_role(
        UserRole.administrator, UserRole.brand_manager, UserRole.reviewer, UserRole.auditor
    )),
) -> AuditVerifyResponse:
    """Verify the integrity of the hash chain for the current org."""
    result = await verify_audit_chain(db, current_user.org_id)
    return AuditVerifyResponse(**result)
