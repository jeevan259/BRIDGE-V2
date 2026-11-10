"""Organisations endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep, require_role
from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.schemas.organisation import (
    OrganisationCreate, OrganisationList, OrganisationResponse, OrganisationUpdate
)

router = APIRouter(prefix="/organisations", tags=["organisations"])


@router.get("", response_model=OrganisationList)
async def list_organisations(
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> OrganisationList:
    # Administrators can see all; others see their own org only
    if current_user.role == UserRole.administrator:
        base = select(Organisation)
        count_base = select(func.count()).select_from(Organisation)
    else:
        base = select(Organisation).where(Organisation.id == current_user.org_id)
        count_base = select(func.count()).select_from(Organisation).where(
            Organisation.id == current_user.org_id
        )

    total = (await db.execute(count_base)).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(Organisation.created_at.desc()).offset(offset).limit(page_size)
    )
    orgs = result.scalars().all()
    return OrganisationList(
        items=[OrganisationResponse.model_validate(o) for o in orgs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=OrganisationResponse, status_code=status.HTTP_201_CREATED)
async def create_organisation(
    body: OrganisationCreate,
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator)),
) -> OrganisationResponse:
    existing = await db.execute(select(Organisation).where(Organisation.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already taken")
    org = Organisation(name=body.name, slug=body.slug)
    db.add(org)
    await db.flush()

    from app.services.audit import append_audit_event
    await append_audit_event(
        db,
        org_id=org.id,
        event_type="ORGANISATION_CREATED",
        actor=current_user,
        resource_type="organisation",
        resource_id=str(org.id),
        diff_json={"name": org.name, "slug": org.slug},
    )
    return OrganisationResponse.model_validate(org)


@router.get("/{org_id}", response_model=OrganisationResponse)
async def get_organisation(
    org_id: uuid.UUID,
    db: DbDep,
    current_user: CurrentUser,
) -> OrganisationResponse:
    if current_user.role != UserRole.administrator and current_user.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    result = await db.execute(select(Organisation).where(Organisation.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return OrganisationResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrganisationResponse)
async def update_organisation(
    org_id: uuid.UUID,
    body: OrganisationUpdate,
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator)),
) -> OrganisationResponse:
    result = await db.execute(select(Organisation).where(Organisation.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    if body.name is not None:
        org.name = body.name
    if body.is_active is not None:
        org.is_active = body.is_active
    await db.flush()

    from app.services.audit import append_audit_event
    await append_audit_event(
        db,
        org_id=org.id,
        event_type="ORGANISATION_UPDATED",
        actor=current_user,
        resource_type="organisation",
        resource_id=str(org.id),
        diff_json={"name": org.name, "is_active": org.is_active},
    )
    return OrganisationResponse.model_validate(org)
