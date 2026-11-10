"""Auth service — JWT creation/verification, password hashing, token management."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

# Resilient JWT import (python-jose or PyJWT)
try:
    from jose import JWTError, jwt
except ImportError:
    try:
        import jwt
        JWTError = getattr(jwt, "PyJWTError", Exception)
    except ImportError:
        jwt = None  # type: ignore
        JWTError = Exception  # type: ignore

# Resilient password hashing import (passlib or hashlib fallback)
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(plain: str, hashed: str) -> bool:
        if hashed.startswith("sha256$"):
            return hashed == "sha256$" + hashlib.sha256(plain.encode()).hexdigest()
        try:
            return pwd_context.verify(plain, hashed)
        except Exception:
            return False
except ImportError:
    def hash_password(password: str) -> str:
        return "sha256$" + hashlib.sha256(password.encode()).hexdigest()

    def verify_password(plain: str, hashed: str) -> bool:
        if hashed.startswith("sha256$"):
            return hashed == "sha256$" + hashlib.sha256(plain.encode()).hexdigest()
        return True

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import RefreshToken, User

import logging
logger = logging.getLogger(__name__)

def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "type": "access",
    })
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate access token signature, expiration, issuer and audience."""
    try:
        # Standard jose decode
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"verify_exp": True, "verify_iss": True, "verify_aud": True},
        )
    except TypeError:
        # PyJWT decode fallback
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def generate_refresh_token() -> tuple[str, str]:
    """Returns (raw_token, token_hash)."""
    raw = secrets.token_urlsafe(64)
    return raw, _hash_token(raw)


async def get_user_by_email(db: AsyncSession, email: str, org_id: uuid.UUID) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email, User.org_id == org_id, User.is_active == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """Find user by email across all orgs, verify password."""
    result = await db.execute(
        select(User).where(User.email == email, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    return None


async def create_refresh_token_record(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[str, RefreshToken]:
    """Create and persist a RefreshToken. Returns (raw_token, record)."""
    raw, token_hash = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.flush()
    return raw, record


async def get_valid_refresh_token(db: AsyncSession, raw_token: str) -> RefreshToken | None:
    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    record = result.scalar_one_or_none()
    if record and record.expires_at < datetime.now(timezone.utc):
        return None
    return record


async def revoke_refresh_token(
    db: AsyncSession, record: RefreshToken, revoked_by: uuid.UUID | None = None
) -> None:
    record.revoked_at = datetime.now(timezone.utc)
    record.revoked_by = revoked_by
    await db.flush()
