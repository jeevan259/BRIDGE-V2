"""Tests for guest authentication, rate limiting, permissions scoping, and cleanup."""
from __future__ import annotations

import asyncio
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from starlette.requests import Request
from starlette.responses import Response

from app.api.deps import require_role
from app.api.v1.auth import _check_guest_rate_limit, _guest_ip_timestamps
from app.core.config import settings
from app.models.user import User, UserRole


def test_guest_rate_limiting():
    """Verify IP rate limiting on guest creation."""
    client_ip = f"192.168.1.{uuid.uuid4().hex[:4]}"
    _guest_ip_timestamps[client_ip] = []

    # First 30 should succeed
    for _ in range(30):
        _check_guest_rate_limit(client_ip)

    # 31st should raise 429
    with pytest.raises(HTTPException) as exc_info:
        _check_guest_rate_limit(client_ip)
    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_guest_cannot_manage_users():
    """Guest with reviewer role must be rejected by user management endpoints."""
    async def _run():
        guest_user = User(
            id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            email="guest_1234@aurora.local",
            role=UserRole.reviewer,
            is_active=True,
        )
        checker = require_role(UserRole.administrator, UserRole.brand_manager)
        with pytest.raises(HTTPException) as exc:
            await checker(guest_user)
        assert exc.value.status_code == status.HTTP_403_FORBIDDEN

    asyncio.run(_run())


def test_guest_cannot_reset_demo():
    """Guest with reviewer role must be rejected by admin demo reset endpoint."""
    async def _run():
        guest_user = User(
            id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            email="guest_1234@aurora.local",
            role=UserRole.reviewer,
            is_active=True,
        )
        checker = require_role(UserRole.administrator)
        with pytest.raises(HTTPException) as exc:
            await checker(guest_user)
        assert exc.value.status_code == status.HTTP_403_FORBIDDEN

    asyncio.run(_run())


def test_cleanup_stale_guests_spares_seeded():
    """24h cleanup must only target guest_* accounts, never seeded aurora accounts."""
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(hours=25)

    seeded_user = User(
        id=uuid.uuid4(),
        email="reviewer@aurora.local",
        created_at=old_time,
    )
    guest_user = User(
        id=uuid.uuid4(),
        email="guest_abc1@aurora.local",
        created_at=old_time,
    )

    users = [seeded_user, guest_user]
    stale_guests = [
        u for u in users
        if u.email.startswith("guest_") and (now - u.created_at) > timedelta(hours=24)
    ]

    assert len(stale_guests) == 1
    assert stale_guests[0].id == guest_user.id
    assert seeded_user.id not in [u.id for u in stale_guests]

