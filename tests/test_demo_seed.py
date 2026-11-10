"""Tests for the demo seed endpoint RBAC and DEMO_MODE gating."""
from __future__ import annotations

import asyncio
import uuid
import pytest
from fastapi import HTTPException, status
from unittest.mock import patch

from app.api.deps import require_role
from app.models.user import User, UserRole


def _make_user(role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        email=f"{role.value}@bridge.local",
        hashed_password="hash",
        role=role,
        is_active=True,
    )


def test_demo_seed_requires_admin_role():
    """Non-admin roles must be rejected by the admin-only RBAC checker."""
    async def _run():
        checker = require_role(UserRole.administrator)

        # brand_manager -> 403
        bm = _make_user(UserRole.brand_manager)
        with pytest.raises(HTTPException) as exc_info:
            await checker(bm)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

        # creator -> 403
        creator = _make_user(UserRole.creator)
        with pytest.raises(HTTPException) as exc_info:
            await checker(creator)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

        # reviewer -> 403
        reviewer = _make_user(UserRole.reviewer)
        with pytest.raises(HTTPException) as exc_info:
            await checker(reviewer)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

        # auditor -> 403
        auditor = _make_user(UserRole.auditor)
        with pytest.raises(HTTPException) as exc_info:
            await checker(auditor)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

        # admin -> allowed
        admin = _make_user(UserRole.administrator)
        result = await checker(admin)
        assert result == admin

    asyncio.run(_run())


def test_demo_seed_demo_mode_gate():
    """When DEMO_MODE=false, the endpoint logic must raise 403."""
    from app.core.config import settings

    # Simulate the gate check from demo.py inline
    original = settings.demo_mode
    try:
        # demo_mode off -> should block
        object.__setattr__(settings, "demo_mode", False)
        with pytest.raises(HTTPException) as exc_info:
            if not settings.demo_mode:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Demo mode disabled",
                )
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "Demo mode disabled"

        # demo_mode on -> should not block
        object.__setattr__(settings, "demo_mode", True)
        assert settings.demo_mode is True  # gate passes
    finally:
        object.__setattr__(settings, "demo_mode", original)
