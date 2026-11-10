"""Users endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbDep, require_role
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserList, UserResponse, UserUpdate
from app.services.auth import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserList)
async def list_users(
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator, UserRole.brand_manager)),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> UserList:
    org_id = current_user.org_id
    offset = (page - 1) * page_size

    total_result = await db.execute(
        select(func.count()).select_from(User).where(User.org_id == org_id)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(User)
        .where(User.org_id == org_id)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    users = result.scalars().all()
    return UserList(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator, UserRole.brand_manager)),
) -> UserResponse:
    # Check email uniqueness within org
    existing = await db.execute(
        select(User).where(User.email == body.email, User.org_id == current_user.org_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered in this org"
        )
    user = User(
        org_id=current_user.org_id,
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()

    from app.services.audit import append_audit_event
    await append_audit_event(
        db,
        org_id=current_user.org_id,
        event_type="USER_CREATED",
        actor=current_user,
        resource_type="user",
        resource_id=str(user.id),
        diff_json={"email": user.email, "role": user.role.value},
    )
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: DbDep,
    current_user: CurrentUser,
) -> UserResponse:
    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == current_user.org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator, UserRole.brand_manager)),
) -> UserResponse:
    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == current_user.org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    await db.flush()

    from app.services.audit import append_audit_event
    await append_audit_event(
        db,
        org_id=current_user.org_id,
        event_type="USER_UPDATED",
        actor=current_user,
        resource_type="user",
        resource_id=str(user.id),
        diff_json={"role": user.role.value, "is_active": user.is_active},
    )
    return UserResponse.model_validate(user)
