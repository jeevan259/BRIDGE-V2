"""Auth endpoints: login, refresh, logout, me."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbDep
from app.config import settings
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token_record,
    get_valid_refresh_token,
    revoke_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_NAME = "bridge_refresh_token"
_COOKIE_MAX_AGE = settings.refresh_token_expire_days * 86400


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: DbDep,
) -> TokenResponse:
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token({"sub": str(user.id), "org": str(user.org_id)})
    raw_refresh, _ = await create_refresh_token_record(db, user.id)

    from app.services.audit import append_audit_event
    await append_audit_event(
        db,
        org_id=user.org_id,
        event_type="AUTH_LOGIN_SUCCESS",
        actor=user,
        resource_type="user",
        resource_id=str(user.id),
        diff_json={"role": user.role.value},
    )

    response.set_cookie(
        key=_COOKIE_NAME,
        value=raw_refresh,
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.resolved_cookie_samesite,
        domain=settings.cookie_domain,
        max_age=_COOKIE_MAX_AGE,
        path="/api/v1/auth",
    )
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    db: DbDep,
    bridge_refresh_token: str | None = Cookie(default=None),
) -> TokenResponse:
    if not bridge_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    record = await get_valid_refresh_token(db, bridge_refresh_token)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Rotate: revoke old, issue new
    await revoke_refresh_token(db, record, revoked_by=record.user_id)
    raw_refresh, _ = await create_refresh_token_record(db, record.user_id)

    access_token = create_access_token({"sub": str(record.user_id)})

    response.set_cookie(
        key=_COOKIE_NAME,
        value=raw_refresh,
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.resolved_cookie_samesite,
        domain=settings.cookie_domain,
        max_age=_COOKIE_MAX_AGE,
        path="/api/v1/auth",
    )
    return TokenResponse(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(
    response: Response,
    db: DbDep,
    current_user: CurrentUser,
    bridge_refresh_token: str | None = Cookie(default=None),
) -> Response:
    if bridge_refresh_token:
        record = await get_valid_refresh_token(db, bridge_refresh_token)
        if record:
            await revoke_refresh_token(db, record, revoked_by=current_user.id)
    from app.services.audit import append_audit_event
    await append_audit_event(
        db,
        org_id=current_user.org_id,
        event_type="AUTH_LOGOUT",
        actor=current_user,
        resource_type="user",
        resource_id=str(current_user.id),
    )
    response.delete_cookie(
        key=_COOKIE_NAME,
        path="/api/v1/auth",
        domain=settings.cookie_domain,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
