"""FastAPI dependencies: DB session, auth, RBAC, org scoping."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.auth import JWTError, decode_access_token, get_user_by_id

async def get_async_session():
    async with AsyncSessionLocal() as session:
        yield session

bearer_scheme = HTTPBearer(auto_error=False)

DbDep = Annotated[AsyncSession, Depends(get_async_session)]


async def get_current_user(
    db: DbDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    """Extract and validate JWT, return current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise credentials_exception

    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str: str | None = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise credentials_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole):
    """Return a dependency that enforces one of the given roles."""
    async def checker(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {[r.value for r in roles]}",
            )
        return current_user
    return checker


def require_min_role(min_role: UserRole):
    """
    Enforce a minimum role based on hierarchy:
    administrator > brand_manager > reviewer > creator > auditor
    """
    _hierarchy = [
        UserRole.administrator,
        UserRole.brand_manager,
        UserRole.reviewer,
        UserRole.creator,
        UserRole.auditor,
    ]

    async def checker(current_user: CurrentUser) -> User:
        try:
            user_level = _hierarchy.index(current_user.role)
            required_level = _hierarchy.index(min_role)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid role")
        if user_level > required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires at least role: {min_role.value}",
            )
        return current_user
    return checker


def org_scope(current_user: CurrentUser) -> uuid.UUID:
    """Return the org_id of the current user for query scoping."""
    return current_user.org_id
