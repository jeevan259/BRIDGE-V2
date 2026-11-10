"""Auth endpoints: login, refresh, logout, me."""
from __future__ import annotations

import secrets
import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbDep, require_role
from app.config import settings
from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token_record,
    get_valid_refresh_token,
    hash_password,
    revoke_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_NAME = "bridge_refresh_token"
_COOKIE_MAX_AGE = settings.refresh_token_expire_days * 86400

# Rate limiter for guest accounts: max 30 per IP per hour
_guest_ip_timestamps: dict[str, list[float]] = defaultdict(list)
_GUEST_RATE_LIMIT = 30
_GUEST_RATE_WINDOW = 3600


def _check_guest_rate_limit(client_ip: str) -> None:
    now = time.time()
    timestamps = [t for t in _guest_ip_timestamps[client_ip] if now - t < _GUEST_RATE_WINDOW]
    if len(timestamps) >= _GUEST_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Guest creation rate limit exceeded. Please wait or sign in.",
        )
    timestamps.append(now)
    _guest_ip_timestamps[client_ip] = timestamps


@router.post("/guest", response_model=TokenResponse)
async def guest_login(
    request: Request,
    response: Response,
    db: DbDep,
) -> TokenResponse:
    """Public instant guest access into Aurora Outdoors tenant with role=reviewer.
    
    DEMO_MODE=true required. Rate-limited per IP, audit-logged.
    """
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guest access is only available in DEMO_MODE",
        )

    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    _check_guest_rate_limit(client_ip)

    org_res = await db.execute(
        select(Organisation).where(Organisation.slug == "aurora-outdoors")
    )
    org = org_res.scalar_one_or_none()
    if not org:
        org_res = await db.execute(select(Organisation).limit(1))
        org = org_res.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Demo organisation not initialized. Please run seeder.",
        )

    guest_uid = secrets.token_hex(4)
    guest_email = f"guest_{guest_uid}@aurora.local"
    guest_name = f"Guest Reviewer #{guest_uid.upper()}"
    random_pw = secrets.token_urlsafe(32)

    guest_user = User(
        org_id=org.id,
        email=guest_email,
        full_name=guest_name,
        role=UserRole.reviewer,
        hashed_password=hash_password(random_pw),
        is_active=True,
    )
    db.add(guest_user)
    await db.flush()

    access_token = create_access_token({"sub": str(guest_user.id), "org": str(org.id)})
    raw_refresh, _ = await create_refresh_token_record(db, guest_user.id)

    from app.services.audit import append_audit_event
    await append_audit_event(
        db,
        org_id=org.id,
        event_type="AUTH_GUEST_LOGIN",
        actor=guest_user,
        resource_type="user",
        resource_id=str(guest_user.id),
        diff_json={"email": guest_email, "role": guest_user.role.value, "client_ip": client_ip},
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


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: DbDep,
) -> TokenResponse:
    """Self-signup in Aurora Outdoors tenant."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    org_res = await db.execute(select(Organisation).where(Organisation.slug == "aurora-outdoors"))
    org = org_res.scalar_one_or_none() or (await db.execute(select(Organisation).limit(1))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Organisation not found")

    new_user = User(
        org_id=org.id,
        email=body.email,
        full_name=body.full_name or body.email.split("@")[0].title(),
        role=UserRole.reviewer,
        hashed_password=hash_password(body.password),
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    access_token = create_access_token({"sub": str(new_user.id), "org": str(org.id)})
    raw_refresh, _ = await create_refresh_token_record(db, new_user.id)

    from app.services.audit import append_audit_event
    await append_audit_event(
        db,
        org_id=org.id,
        event_type="AUTH_USER_REGISTERED",
        actor=new_user,
        resource_type="user",
        resource_id=str(new_user.id),
        diff_json={"email": body.email, "role": new_user.role.value},
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


@router.post("/cleanup-guests", status_code=status.HTTP_200_OK)
async def cleanup_guests(
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator)),
) -> dict:
    """Delete guest users and their data older than 24h. Never deletes seeded accounts."""
    from datetime import timedelta
    from sqlalchemy import delete
    from app.models.validation import ValidationJob
    from app.models.user import RefreshToken

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    stale_users = (await db.execute(
        select(User).where(User.email.like("guest_%"), User.created_at < cutoff)
    )).scalars().all()
    count = len(stale_users)
    if stale_users:
        stale_ids = [u.id for u in stale_users]
        await db.execute(delete(ValidationJob).where(ValidationJob.submitted_by.in_(stale_ids)))
        await db.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(stale_ids)))
        await db.execute(delete(User).where(User.id.in_(stale_ids)))
        await db.flush()

    return {"deleted_guests_count": count}


_auth_ip_timestamps: dict[str, list[datetime]] = {}


def _check_auth_rate_limit(client_ip: str) -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=15)
    timestamps = [t for t in _auth_ip_timestamps.get(client_ip, []) if t > cutoff]
    if len(timestamps) >= 60:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
        )
    timestamps.append(now)
    _auth_ip_timestamps[client_ip] = timestamps


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: DbDep,
) -> TokenResponse:
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    _check_auth_rate_limit(client_ip)

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
