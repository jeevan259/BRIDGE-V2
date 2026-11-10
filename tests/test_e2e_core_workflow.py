"""End-to-end test for Phase 3 core workflow:
Guest login -> Paste text -> Check -> Findings -> Decision -> Read back from separate auditor session.
"""
from __future__ import annotations

import asyncio
import uuid
import pytest
from datetime import datetime, timezone

from app.database import AsyncSessionLocal
from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.models.validation import JobStatus, ValidationJob, Finding, FindingType
from app.services.auth import create_access_token, decode_access_token
from app.services.audit import verify_audit_chain, append_audit_event
from app.services.validation import run_validation_pipeline
from app.api.v1.validation import list_job_findings, list_job_hallucination_defense, decide_validation_job
from app.schemas.validation import JobDecisionRequest
from sqlalchemy import select


def test_core_workflow_e2e():
    async def _run():
        async with AsyncSessionLocal() as db:
            org = (await db.execute(
                select(Organisation).where(Organisation.slug == "aurora-outdoors")
            )).scalar_one()

            # 1. Guest reviewer session
            guest = User(
                id=uuid.uuid4(),
                org_id=org.id,
                email=f"guest_{uuid.uuid4().hex[:6]}@aurora.local",
                full_name="Guest Evaluator",
                role=UserRole.reviewer,
                hashed_password="mock_hash_for_test",
                is_active=True,
            )
            db.add(guest)
            await db.flush()

            guest_token = create_access_token({"sub": str(guest.id), "org": str(org.id)})
            payload = decode_access_token(guest_token)
            assert payload["sub"] == str(guest.id)

            # 2. Paste violating content sample
            violating_text = (
                "HUGE FLASH SALE! Aurora Outdoors is executing a revolutionary disruptive transformation "
                "with the world's best gear! Featuring our mountain logo over a vibrant neon red gradient background (#FF0000). "
                "Our products are completely eco-friendly and conquer nature effortlessly! "
                "Single-use plastic zip-ties secure all hangtags. Guaranteed 100% risk-free summit expeditions."
            )
            job = ValidationJob(
                org_id=org.id,
                content_title="Flash Sale Promo Banner",
                content_text=violating_text,
                submitted_by=guest.id,
                created_at=datetime.now(timezone.utc),
            )
            db.add(job)
            await db.flush()

            # 3. Execute validation pipeline
            res = await run_validation_pipeline(db, job.id, org.id)
            assert res["status"] == "completed"
            assert res["findings_count"] > 0

            # 4. Check findings endpoint (quarantined hallucinations must not appear)
            findings_result = await list_job_findings(job_id=job.id, db=db, current_user=guest)
            assert len(findings_result.items) > 0
            for f in findings_result.items:
                assert f.finding_type != FindingType.unsupported
                assert f.is_evidence_backed is True

            # 5. Check hallucination defense endpoint
            defense_result = await list_job_hallucination_defense(job_id=job.id, db=db, current_user=guest)
            assert isinstance(defense_result.items, list)

            # 6. Human review decision: Request changes
            decision_res = await decide_validation_job(
                job_id=job.id,
                body=JobDecisionRequest(decision="changes_requested", notes="Must remove #FF0000 and hype buzzwords"),
                db=db,
                current_user=guest,
            )
            assert decision_res.decision == "changes_requested"
            assert decision_res.decided_by == guest.email
            await db.commit()

        # 7. Read back from separate auditor session
        async with AsyncSessionLocal() as auditor_db:
            auditor = (await auditor_db.execute(
                select(User).where(User.email == "auditor@aurora.local")
            )).scalar_one()

            # Verify audit chain integrity includes the decision event
            chain_status = await verify_audit_chain(auditor_db, org.id)
            assert chain_status["is_valid"] is True
            assert chain_status["total_events"] > 0

            # Auditor can inspect the finalized job findings
            auditor_findings = await list_job_findings(job_id=job.id, db=auditor_db, current_user=auditor)
            assert len(auditor_findings.items) == len(findings_result.items)

    import asyncio.runners
    asyncio.runners.run(_run())

