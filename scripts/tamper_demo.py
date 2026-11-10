"""Tamper demonstration script for BRIDGE tamper-evident audit ledger.

Demonstrates:
1. Verifies that an audit chain is intact.
2. Creates sequential audit events with canonical hash-chaining.
3. Simulates an adversary altering a historical event payload.
4. Confirms that verify_audit_chain detects the discrepancy and pinpoints the exact broken event ID.
5. Restores original data to prove chain integrity recovery.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Ensure api directory is on Python path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "api"))

# Mock asyncpg if not installed locally
if "asyncpg" not in sys.modules:
    try:
        import asyncpg
    except ImportError:
        mock_asyncpg = MagicMock()
        mock_asyncpg.exceptions = MagicMock()
        sys.modules["asyncpg"] = mock_asyncpg
        sys.modules["asyncpg.exceptions"] = mock_asyncpg.exceptions

from app.models.audit import AuditEvent
from app.models.organisation import Organisation
from app.services.audit import _canonical_serialize, _compute_hash, append_audit_event, verify_audit_chain

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tamper_demo")


async def run_tamper_demo() -> None:
    logger.info("==========================================================")
    logger.info("  BRIDGE V2: Tamper-Evident Audit Ledger Demonstration    ")
    logger.info("==========================================================")

    org_id = uuid.uuid4()
    events: list[AuditEvent] = []
    prev_hash = None

    logger.info("\n--- Phase 1: Building Valid Canonical Audit Chain ---")
    logger.info("Simulating sequential governance events for Org %s...", org_id)

    # 1. Build initial sequence of events
    actions = [
        ("KNOWLEDGE_INGESTED", "source", "src-brand-guide-2026", {"title": "Apex Brand Guidelines 2026"}),
        ("RULE_APPROVED", "rule", "R-001", {"name": "Primary Logo Exclusion Zone", "clearance": "0.5x"}),
        ("CONTENT_VALIDATED", "content", "cnt-q3-campaign", {"status": "violations_found", "count": 2}),
        ("OVERRIDE_RECORDED", "finding", "fnd-9821", {"reason": "Approved by CMO", "code": "EXECUTIVE_EXCEPTION"}),
    ]

    for idx, (event_type, res_type, res_id, diff) in enumerate(actions, start=1):
        now = datetime.now(timezone.utc)
        event_id = uuid.uuid4()
        payload = {
            "id": str(event_id),
            "org_id": str(org_id),
            "event_type": event_type,
            "actor_id": None,
            "actor_email": "admin@apextech.com",
            "resource_type": res_type,
            "resource_id": res_id,
            "diff_json": diff,
            "outcome": "success",
            "correlation_id": f"corr-demo-{idx}",
            "prev_hash": prev_hash,
            "created_at": now.isoformat(),
        }
        event_hash = _compute_hash(_canonical_serialize(payload))

        ev = AuditEvent(
            id=event_id,
            org_id=org_id,
            event_type=event_type,
            actor_id=None,
            actor_email="admin@apextech.com",
            resource_type=res_type,
            resource_id=res_id,
            diff_json=diff,
            outcome="success",
            correlation_id=f"corr-demo-{idx}",
            prev_hash=prev_hash,
            event_hash=event_hash,
            created_at=now,
        )
        events.append(ev)
        logger.info(
            "  [Event %d] ID: %s | Action: %-20s | Prev: %-10s... | Hash: %-10s...",
            idx,
            str(event_id)[:8],
            event_type,
            prev_hash[:10] if prev_hash else "GENESIS",
            event_hash[:10],
        )
        prev_hash = event_hash

    # Verify baseline chain
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = events
    mock_db.execute = AsyncMock(return_value=mock_result)

    logger.info("\n--- Phase 2: Verifying Intact Audit Chain ---")
    verification = await verify_audit_chain(mock_db, org_id)
    logger.info("  Verification Status : %s", "VALID (Chain Intact)" if verification["is_valid"] else "INVALID")
    logger.info("  Total Events Checked: %d", verification["total_events"])
    logger.info("  Chain Message       : %s", verification["message"])
    assert verification["is_valid"] is True, "Initial chain must be valid!"

    # 2. Tampering Phase
    logger.info("\n--- Phase 3: Adversarial Tamper Simulation ---")
    tampered_index = 1  # Alter RULE_APPROVED event
    target_event = events[tampered_index]
    original_diff = copy.deepcopy(target_event.diff_json)

    logger.info(
        "Adversary attempts silent SQL modification of historical Event #%d (ID: %s)...",
        tampered_index + 1,
        target_event.id,
    )
    logger.info("Original diff_json: %s", original_diff)
    # Alter the clearance rule maliciously
    target_event.diff_json = {"name": "Primary Logo Exclusion Zone", "clearance": "0.1x"}
    logger.info("Tampered diff_json: %s", target_event.diff_json)

    logger.info("\n--- Phase 4: Detecting Ledger Discrepancy ---")
    tamper_result = await verify_audit_chain(mock_db, org_id)
    logger.info("  Verification Status : %s", "INVALID (Tamper Detected!)" if not tamper_result["is_valid"] else "VALID")
    logger.info("  Broken Event ID     : %s", tamper_result["broken_at"])
    logger.info("  Diagnostic Detail   : %s", tamper_result["message"])

    assert tamper_result["is_valid"] is False, "Tampered event MUST cause verification failure!"
    assert tamper_result["broken_at"] == target_event.id, "Verification must pinpoint the exact tampered record!"
    logger.info(">>> SUCCESS: Tamper was caught immediately! Cryptographic hash chain failed at event %s", target_event.id)

    # 3. Restoration Phase
    logger.info("\n--- Phase 5: Restoring Ledger State ---")
    target_event.diff_json = original_diff
    restored_result = await verify_audit_chain(mock_db, org_id)
    logger.info("  Verification Status : %s", "RESTORED (Valid)" if restored_result["is_valid"] else "FAILED")
    logger.info("  Chain Message       : %s", restored_result["message"])
    assert restored_result["is_valid"] is True, "Restored ledger must pass verification!"

    logger.info("\n==========================================================")
    logger.info("  Tamper Demonstration Complete: LEDGER INTEGRITY PROVEN  ")
    logger.info("==========================================================")


def _run_sync(coro):
    stack = [coro.__await__() if hasattr(coro, "__await__") else coro]
    res = None
    while stack:
        curr = stack[-1]
        try:
            val = curr.send(res)
            res = None
            if hasattr(val, "__await__"):
                stack.append(val.__await__())
        except StopIteration as exc:
            stack.pop()
            res = exc.value
    return res


if __name__ == "__main__":
    _run_sync(run_tamper_demo())
