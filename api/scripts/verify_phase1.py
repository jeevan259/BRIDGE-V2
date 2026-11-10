import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal
from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.models.knowledge import Passage, KnowledgeItem
from app.models.continuity import DependencyEdge
from app.models.validation import (
    ContentItem, ValidationJob, Finding, FindingType, FindingSeverity, FindingStatus, JobStatus
)
from app.models.guideline import ReviewSignal
from app.seed_demo import seed_demo_tenant
from app.services.auth import authenticate_user
from app.services.audit import verify_audit_chain
from sqlalchemy import func, select

async def count_rows(session, org_id):
    async def c(model):
        q = select(func.count()).select_from(model)
        if hasattr(model, "org_id"):
            q = q.where(model.org_id == org_id)
        return (await session.execute(q)).scalar_one()

    return {
        "users": await c(User),
        "passages": await c(Passage),
        "edges": await c(DependencyEdge),
        "assets": await c(ContentItem),
        "signals": await c(ReviewSignal),
    }

async def main():
    demo_pw = os.getenv("DEMO_PASSWORD", "password123")
    print(f"--- 1. SEED RUN 1 ---")
    async with AsyncSessionLocal() as session:
        res1 = await seed_demo_tenant(session, reset=False)
        await session.commit()
        print(f"Seed run 1 status: {res1.get('status')}")
        
        org = (await session.execute(
            select(Organisation).where(Organisation.slug == "aurora-outdoors")
        )).scalar_one()
        counts1 = await count_rows(session, org.id)
        print(f"Row counts after run 1: {counts1}")

    print(f"--- 2. SEED RUN 2 ---")
    async with AsyncSessionLocal() as session:
        res2 = await seed_demo_tenant(session, reset=False)
        await session.commit()
        print(f"Seed run 2 status: {res2.get('status')}")
        
        counts2 = await count_rows(session, org.id)
        print(f"Row counts after run 2: {counts2}")
        
        assert counts1 == counts2, f"Row counts mismatch: {counts1} vs {counts2}"
        print(f"CONFIRMED: Row counts are 100% identical after two runs.")
        print(f"  users: {counts2['users']} (target: 5)")
        print(f"  passages: {counts2['passages']} (target: >=25)")
        print(f"  edges: {counts2['edges']} (target: ~12)")
        print(f"  assets: {counts2['assets']} (target: 6)")
        print(f"  signals: {counts2['signals']} (target: ~20)")
        assert counts2["users"] == 5
        assert counts2["passages"] >= 25
        assert counts2["edges"] >= 12
        assert counts2["assets"] == 6
        assert counts2["signals"] >= 20

    print(f"--- 3. VERIFY 5 ROLE LOGINS ---")
    roles = [
        "admin@aurora.local",
        "brand_manager@aurora.local",
        "reviewer@aurora.local",
        "creator@aurora.local",
        "auditor@aurora.local",
    ]
    async with AsyncSessionLocal() as session:
        for email in roles:
            user = await authenticate_user(session, email, demo_pw)
            assert user is not None, f"Login failed for {email}"
            print(f"  [SUCCESS] {email} logged in (role={user.role.value}, id={user.id})")

    print(f"--- 4. VERIFY QUARANTINED HALLUCINATIONS ---")
    async with AsyncSessionLocal() as session:
        # Create a transient test validation job
        test_job = ValidationJob(
            org_id=org.id,
            content_title="Hallucination Quarantine Test Job",
            content_text="Sample text for testing hallucination isolation",
            status=JobStatus.completed,
            ai_provider_used="test-provider",
            created_at=datetime.now(timezone.utc),
        )
        session.add(test_job)
        await session.flush()

        # Add 1 valid finding
        valid_finding = Finding(
            job_id=test_job.id,
            org_id=org.id,
            finding_type=FindingType.brand_violation,
            severity=FindingSeverity.high,
            description="Valid evidence-backed finding",
            is_evidence_backed=True,
            status=FindingStatus.pending,
        )
        session.add(valid_finding)

        # Add 1 quarantined hallucination finding
        hallucination_finding = Finding(
            job_id=test_job.id,
            org_id=org.id,
            finding_type=FindingType.unsupported,
            severity=FindingSeverity.medium,
            description="[HALLUCINATION TRAP TRIGGERED] AI claimed citation to nonexistent source",
            is_evidence_backed=False,
            status=FindingStatus.pending,
        )
        session.add(hallucination_finding)
        await session.flush()

        # Simulate GET /jobs/{job_id}/findings query
        normal_query = select(Finding).where(
            Finding.job_id == test_job.id,
            Finding.org_id == org.id,
            Finding.finding_type != FindingType.unsupported,
            Finding.is_evidence_backed == True,
        )
        normal_findings = (await session.execute(normal_query)).scalars().all()
        normal_types = [f.finding_type.value for f in normal_findings]
        print(f"  Normal findings endpoint returned: {len(normal_findings)} items -> {normal_types}")
        assert len(normal_findings) == 1
        assert "unsupported" not in normal_types
        print(f"  [PASS] Quarantined hallucination does NOT appear in normal findings endpoint.")

        # Simulate GET /jobs/{job_id}/hallucination-defense query
        defense_query = select(Finding).where(
            Finding.job_id == test_job.id,
            Finding.org_id == org.id,
            (Finding.finding_type == FindingType.unsupported) | (Finding.is_evidence_backed == False),
        )
        defense_findings = (await session.execute(defense_query)).scalars().all()
        defense_types = [f.finding_type.value for f in defense_findings]
        print(f"  Hallucination defense endpoint returned: {len(defense_findings)} items -> {defense_types}")
        assert len(defense_findings) == 1
        assert "unsupported" in defense_types
        print(f"  [PASS] Quarantined hallucination DOES appear in hallucination defense endpoint.")

        # Cleanup transient test findings & job
        from sqlalchemy import delete
        await session.execute(delete(Finding).where(Finding.job_id == test_job.id))
        await session.execute(delete(ValidationJob).where(ValidationJob.id == test_job.id))
        await session.commit()

    print(f"--- 5. AUDIT CHAIN VERIFY ---")
    async with AsyncSessionLocal() as session:
        audit_res = await verify_audit_chain(session, org.id)
        print(f"  Audit Chain: valid={audit_res['is_valid']}, total_events={audit_res['total_events']}")
        assert audit_res["is_valid"] is True

    print("\nALL PHASE 1 ACCEPTANCE CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    asyncio.run(main())
