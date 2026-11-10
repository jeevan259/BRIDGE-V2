"""Tests for Role-Based Access Control (RBAC) across all 5 user roles."""
from __future__ import annotations

import asyncio
import uuid
import pytest
from fastapi import HTTPException, status

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


def test_admin_role_permissions():
    """Administrator must have access to admin-only and management endpoints."""
    async def _run():
        admin = _make_user(UserRole.administrator)
        checker = require_role(UserRole.administrator)

        # Allowed
        result = await checker(admin)
        assert result == admin

        # Allowed in multi-role endpoints
        mgmt_checker = require_role(UserRole.administrator, UserRole.brand_manager)
        assert await mgmt_checker(admin) == admin

    asyncio.run(_run())


def test_creator_role_forbidden_from_admin_and_review():
    """Creator must be denied from reviewer and administrator actions."""
    async def _run():
        creator = _make_user(UserRole.creator)

        # Denied from admin endpoints
        admin_checker = require_role(UserRole.administrator)
        with pytest.raises(HTTPException) as exc_info:
            await admin_checker(creator)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

        # Denied from review approval
        creator_checker = require_role(UserRole.administrator, UserRole.brand_manager)
        with pytest.raises(HTTPException) as exc_info:
            await creator_checker(creator)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    asyncio.run(_run())


def test_reviewer_allowed_to_review_denied_from_user_admin():
    """Reviewer can override/review findings but cannot administer users."""
    async def _run():
        reviewer = _make_user(UserRole.reviewer)

        # Reviewer allowed
        review_checker = require_role(UserRole.administrator, UserRole.brand_manager, UserRole.reviewer)
        assert await review_checker(reviewer) == reviewer

        # Reviewer denied from user management
        admin_checker = require_role(UserRole.administrator)
        with pytest.raises(HTTPException) as exc_info:
            await admin_checker(reviewer)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    asyncio.run(_run())


def test_auditor_read_only_access():
    """Auditor is denied from modifying knowledge items or overriding findings."""
    async def _run():
        auditor = _make_user(UserRole.auditor)

        # Denied from knowledge authoring
        author_checker = require_role(UserRole.administrator, UserRole.brand_manager)
        with pytest.raises(HTTPException) as exc_info:
            await author_checker(auditor)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

        # Denied from finding override
        override_checker = require_role(UserRole.administrator, UserRole.brand_manager, UserRole.reviewer)
        with pytest.raises(HTTPException) as exc_info:
            await override_checker(auditor)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    asyncio.run(_run())


def test_brand_manager_permissions():
    """Brand Manager can manage knowledge sources and items, but cannot administer users."""
    async def _run():
        bm = _make_user(UserRole.brand_manager)

        # Allowed to manage knowledge
        km_checker = require_role(UserRole.administrator, UserRole.brand_manager)
        assert await km_checker(bm) == bm

        # Denied from user administration
        admin_checker = require_role(UserRole.administrator)
        with pytest.raises(HTTPException) as exc_info:
            await admin_checker(bm)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    asyncio.run(_run())
