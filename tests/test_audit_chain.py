"""Tests for tamper-evident hash-chained audit service."""
from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.audit import AuditEvent
from app.models.user import User, UserRole
from app.services.audit import _canonical_serialize, _compute_hash, _build_hash_payload, verify_audit_chain


def test_canonical_serialization_deterministic():
    """Verify serialization is deterministic regardless of key insertion order."""
    payload1 = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
    payload2 = {"a": 1, "nested": {"y": 8, "z": 9}, "b": 2}

    assert _canonical_serialize(payload1) == _canonical_serialize(payload2)
    assert _compute_hash(_canonical_serialize(payload1)) == _compute_hash(_canonical_serialize(payload2))


def _make_chained_events(count: int) -> list[AuditEvent]:
    """Create a valid hash-chained sequence of AuditEvents."""
    org_id = uuid.uuid4()
    events: list[AuditEvent] = []
    prev_hash = None

    for i in range(count):
        now = datetime.now(timezone.utc)
        event_id = uuid.uuid4()
        payload = _build_hash_payload(
            event_id=event_id,
            org_id=org_id,
            event_type=f"EVENT_TYPE_{i}",
            actor_id=None,
            actor_email="test@bridge.local",
            resource_type="item",
            resource_id=f"item-{i}",
            diff_json={"step": i},
            outcome="success",
            correlation_id="test-cid",
            prev_hash=prev_hash,
            created_at=now,
        )
        event_hash = _compute_hash(_canonical_serialize(payload))

        ev = AuditEvent(
            id=event_id,
            org_id=org_id,
            event_type=f"EVENT_TYPE_{i}",
            actor_id=None,
            actor_email="test@bridge.local",
            resource_type="item",
            resource_id=f"item-{i}",
            diff_json={"step": i},
            outcome="success",
            correlation_id="test-cid",
            prev_hash=prev_hash,
            event_hash=event_hash,
            created_at=now,
        )
        events.append(ev)
        prev_hash = event_hash

    return events


def test_audit_chain_verification_intact():
    """Verify that a sequence of chained audit events passes verification."""
    async def _run():
        events = _make_chained_events(5)
        org_id = events[0].org_id

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        mock_db.execute = AsyncMock(return_value=mock_result)

        verification = await verify_audit_chain(mock_db, org_id)
        assert verification["is_valid"] is True
        assert verification["total_events"] == 5
        assert verification["broken_at"] is None
        assert verification["message"] == "Chain intact"

    asyncio.run(_run())


def test_audit_chain_verification_detects_tampering():
    """Verify that altering a single field in a past event breaks verification."""
    async def _run():
        events = _make_chained_events(4)
        org_id = events[0].org_id

        # Tamper with Event 1's payload
        tampered_event_id = events[1].id
        events[1].diff_json = {"val": 9999}  # Modified!

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        mock_db.execute = AsyncMock(return_value=mock_result)

        verification = await verify_audit_chain(mock_db, org_id)
        assert verification["is_valid"] is False
        assert verification["valid"] is False
        assert verification["broken_at"] == tampered_event_id
        assert verification["first_broken_seq"] == 2
        assert "Tampering detected" in verification["message"] or "Hash mismatch" in verification["message"]

    asyncio.run(_run())


def test_audit_verify_response_model():
    """Verify AuditVerifyResponse schema has required fields valid, checked_count, first_broken_seq."""
    from app.schemas.audit import AuditVerifyResponse

    resp = AuditVerifyResponse(
        is_valid=True,
        total_events=12,
        broken_at=None,
        message="Chain intact",
    )
    assert resp.valid is True
    assert resp.checked_count == 12
    assert resp.first_broken_seq is None


def test_audit_chain_empty():
    """Verify empty chain returns valid."""
    async def _run():
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        verification = await verify_audit_chain(mock_db, uuid.uuid4())
        assert verification["is_valid"] is True
        assert verification["total_events"] == 0

    asyncio.run(_run())


def test_audit_chain_single_event():
    """Single-event chain must validate."""
    async def _run():
        events = _make_chained_events(1)
        org_id = events[0].org_id

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        mock_db.execute = AsyncMock(return_value=mock_result)

        verification = await verify_audit_chain(mock_db, org_id)
        assert verification["is_valid"] is True
        assert verification["total_events"] == 1

    asyncio.run(_run())


def test_hash_computation_reproducible():
    """Same input always yields same hash."""
    data = '{"a": 1, "b": 2}'
    h1 = _compute_hash(data)
    h2 = _compute_hash(data)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest
