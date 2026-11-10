"""Verification script for Tamper Demo and Blast Radius Check.
Ensures zero credentials printed and provides raw redacted evidence output.
"""
from __future__ import annotations

import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["DEMO_MODE"] = "true"

from app.config import settings
settings.demo_mode = True

from app.database import AsyncSessionLocal
from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.services.audit import verify_audit_chain
from app.services.continuity import simulate_rule_or_source_change, apply_rule_or_source_change
from sqlalchemy import select, text


async def main() -> None:
    print("=" * 60)
    print("BRIDGE v2: TAMPER DEMO & BLAST RADIUS ACCEPTANCE CHECKS")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        org = (await db.execute(
            select(Organisation).where(Organisation.slug == "aurora-outdoors")
        )).scalar_one()

        admin = (await db.execute(
            select(User).where(User.org_id == org.id, User.role == UserRole.administrator)
        )).scalars().first()

        # -------------------------------------------------------------
        # PART 1: TAMPER DEMO VERIFICATION
        # -------------------------------------------------------------
        print("\n--- PART 1: TAMPER DEMO ---")
        # 1. Baseline verification
        baseline_verify = await verify_audit_chain(db, org.id)
        print("[1] Baseline Audit Chain Verify:")
        print(f"    valid:            {baseline_verify['valid']}")
        print(f"    checked_count:    {baseline_verify['checked_count']}")
        print(f"    first_broken_seq: {baseline_verify['first_broken_seq']}")
        print(f"    message:          {baseline_verify['message']}")
        assert baseline_verify["valid"] is True, "Expected baseline audit chain to be valid"

        # 2. Simulate Attacker Tampering (via trigger bypass in transaction)
        print("\n[2] Executing Tamper (Attacker mutating record behind the scenes)...")
        from app.models.audit import AuditEvent
        latest_event = (await db.execute(
            select(AuditEvent)
            .where(AuditEvent.org_id == org.id)
            .order_by(AuditEvent.created_at.desc())
            .limit(1)
        )).scalar_one()

        orig_outcome = latest_event.outcome
        try:
            await db.execute(text("ALTER TABLE audit_events DISABLE TRIGGER trg_block_audit_mutation"))
            latest_event.outcome = "tampered_unauthorized_override"
            await db.flush()
        finally:
            await db.execute(text("ALTER TABLE audit_events ENABLE TRIGGER trg_block_audit_mutation"))
        await db.commit()

        # 3. Verify Chain detects tampering
        tampered_verify = await verify_audit_chain(db, org.id)
        print("[3] Tampered Audit Chain Verify:")
        print(f"    valid:            {tampered_verify['valid']}")
        print(f"    checked_count:    {tampered_verify['checked_count']}")
        print(f"    first_broken_seq: {tampered_verify['first_broken_seq']}")
        print(f"    message:          {tampered_verify['message']}")
        assert tampered_verify["valid"] is False, "Expected tampered audit chain to fail verification"
        assert tampered_verify["first_broken_seq"] is not None

        # 4. Restore Chain (Untamper)
        print("\n[4] Executing Untamper (Restoring valid cryptographic state)...")
        try:
            await db.execute(text("ALTER TABLE audit_events DISABLE TRIGGER trg_block_audit_mutation"))
            latest_event.outcome = orig_outcome
            await db.flush()
        finally:
            await db.execute(text("ALTER TABLE audit_events ENABLE TRIGGER trg_block_audit_mutation"))
        await db.commit()

        restored_verify = await verify_audit_chain(db, org.id)
        print("[5] Restored Audit Chain Verify:")
        print(f"    valid:            {restored_verify['valid']}")
        print(f"    checked_count:    {restored_verify['checked_count']}")
        print(f"    first_broken_seq: {restored_verify['first_broken_seq']}")
        print(f"    message:          {restored_verify['message']}")
        assert restored_verify["valid"] is True, "Expected restored audit chain to be valid"

        # -------------------------------------------------------------
        # PART 2: BLAST RADIUS CHECK
        # -------------------------------------------------------------
        print("\n--- PART 2: BLAST RADIUS CHECK ---")
        # 1. Simulate Clearspace Rule Change
        print("[1] Simulating Seeded Clearspace Rule Change...")
        sim_result = await simulate_rule_or_source_change(
            db,
            org_id=org.id,
            rule_name="Logo Clearspace Standard",
            change_summary="Update clearspace standard padding to 40px minimum",
        )
        print(f"    rule_name:                 {sim_result['rule_name']}")
        print(f"    impacted_guidelines_count: {sim_result['impacted_guidelines_count']}")
        print(f"    impacted_guidelines:       {json.dumps(sim_result['impacted_guidelines'], indent=4)}")
        print(f"    impacted_assets_count:     {sim_result['impacted_assets_count']}")
        print(f"    impacted_assets:           {json.dumps(sim_result['impacted_assets'], indent=4)}")
        print(f"    blast_radius_score:        {sim_result['blast_radius_score']}")
        print(f"    revalidation_queued:       {sim_result['revalidation_queued']}")

        assert sim_result["impacted_guidelines_count"] >= 3, (
            f"Expected >=3 impacted guidelines, got {sim_result['impacted_guidelines_count']}"
        )
        assert sim_result["impacted_assets_count"] >= 2, (
            f"Expected >=2 impacted assets, got {sim_result['impacted_assets_count']}"
        )
        assert sim_result["revalidation_queued"] is False

        # 2. Apply Change and Queue Revalidation
        print("\n[2] Applying Change and Queuing Revalidation...")
        apply_result = await apply_rule_or_source_change(
            db,
            org_id=org.id,
            actor=admin,
            rule_name="Logo Clearspace Standard",
            change_summary="Mandate modern 40px clearspace standard across all surfaces",
        )
        await db.commit()

        print(f"    applied:                   {apply_result['applied']}")
        print(f"    change_event_id:           {apply_result['change_event_id']}")
        print(f"    impact_report_id:          {apply_result['impact_report_id']}")
        print(f"    impacted_guidelines_count: {apply_result['impacted_guidelines_count']}")
        print(f"    impacted_assets_count:     {apply_result['impacted_assets_count']}")
        print(f"    blast_radius_score:        {apply_result['blast_radius_score']}")
        print(f"    tasks_enqueued:            {apply_result['tasks_enqueued']}")
        print(f"    revalidation_queued:       {apply_result['revalidation_queued']}")

        assert apply_result["applied"] is True
        assert apply_result["impacted_guidelines_count"] >= 3
        assert apply_result["impacted_assets_count"] >= 2
        assert apply_result["tasks_enqueued"] >= 2
        assert apply_result["revalidation_queued"] is True

        # 3. Post-apply audit verification
        post_verify = await verify_audit_chain(db, org.id)
        print(f"\n[3] Post-Apply Audit Chain Verify: valid={post_verify['valid']}, count={post_verify['checked_count']}")
        assert post_verify["valid"] is True

        print("\n" + "=" * 60)
        print("ALL TAMPER DEMO & BLAST RADIUS CHECKS PASSED!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
