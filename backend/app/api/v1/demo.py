"""Demo seeding endpoint.

POST /demo/seed — seeds the Aurora Outdoors demo tenant.
Only accessible when DEMO_MODE=true and the caller is an administrator.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbDep, require_role
from app.core.config import settings
from app.models.user import User, UserRole
from app.seed_demo import seed_demo_tenant
from app.services.audit import append_audit_event

router = APIRouter(prefix="/demo", tags=["demo"])


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
