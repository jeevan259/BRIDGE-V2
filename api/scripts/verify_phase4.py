"""Phase 4 verification script:
1. Sets AI_PROVIDER=gemini, DEMO_MODE=true.
2. Probes GET /api/v1/ai/status (mode, model, last_error).
3. Re-embeds all tenant passages (768d, never mixing mock and live vectors).
4. Runs validation on violating sample, checking provider, fallback_used, finding count, receipts.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set environment
os.environ["AI_PROVIDER"] = "gemini"
os.environ["DEMO_MODE"] = "true"

from app.config import settings
settings.ai_provider = "gemini"
settings.demo_mode = True

from app.database import AsyncSessionLocal
from app.models.organisation import Organisation
from app.models.knowledge import Passage
from app.models.validation import ValidationJob, Finding, FindingType, EvidenceReceipt
from app.models.user import User, UserRole
from app.ai.gemini import get_ai_status, get_embedding_provider, get_llm_provider
from app.services.validation import run_validation_pipeline
from sqlalchemy import select, func


async def verify_phase4():
    print("=" * 60)
    print("BRIDGE v2 — PHASE 4: LIVE AI & FALLBACK VERIFICATION")
    print("=" * 60)

    # 1. Check AI status
    ai_status = await get_ai_status()
    print(f"\n[1] /api/v1/ai/status output:")
    print(f"    Provider:   {ai_status['provider']}")
    print(f"    Mode:       {ai_status['mode']}")
    print(f"    Model:      {ai_status['model']}")
    print(f"    Last Error: {ai_status['last_error']}")

    async with AsyncSessionLocal() as db:
        org = (await db.execute(
            select(Organisation).where(Organisation.slug == "aurora-outdoors")
        )).scalar_one()

        reviewer = (await db.execute(
            select(User).where(User.org_id == org.id, User.role == UserRole.reviewer)
        )).scalars().first()

        # 2. Re-embed all tenant passages
        print(f"\n[2] Re-embedding passages for tenant: {org.name} ({org.slug})")
        passages = (await db.execute(
            select(Passage).where(Passage.org_id == org.id).order_by(Passage.passage_index)
        )).scalars().all()
        passage_count = len(passages)
        print(f"    Passage count: {passage_count}")

        embedder = get_embedding_provider()
        texts = [p.text for p in passages]
        embed_res = await embedder.embed(texts)
        
        print(f"    Embedding Provider: {embed_res.provider}")
        print(f"    Fallback Used:      {embed_res.fallback_used}")
        print(f"    Dimensions:         {embed_res.dimensions}")
        print(f"    Model:              {embed_res.model}")

        assert embed_res.dimensions == 768, f"Expected 768 dimensions, got {embed_res.dimensions}"

        # Update passages - never mix mock and live vectors in pgvector column
        for idx, p in enumerate(passages):
            vec = embed_res.embeddings[idx]
            if embed_res.provider == "gemini" and not embed_res.fallback_used:
                p.embedding_vector = vec
                p.embedding_json = None
            else:
                p.embedding_vector = None
                p.embedding_json = vec

        org.embedding_provider = embed_res.provider
        org.embedding_model = embed_res.model
        await db.commit()
        print(f"    [PASS] Successfully re-embedded {passage_count} passages (768d, no mixed vectors).")

        # 3. Run validation on violating sample
        print(f"\n[3] Running validation on violating sample...")
        violating_text = (
            "HUGE FLASH SALE! Aurora Outdoors is executing a revolutionary disruptive transformation "
            "with the world's best gear! Featuring our mountain logo over a vibrant neon red gradient background (#FF0000). "
            "Our products are completely eco-friendly and conquer nature effortlessly! "
            "Single-use plastic zip-ties secure all hangtags. Guaranteed 100% risk-free summit expeditions."
        )

        job = ValidationJob(
            org_id=org.id,
            content_title="Phase 4 Validation Check",
            content_text=violating_text,
            submitted_by=reviewer.id if reviewer else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.flush()

        res = await run_validation_pipeline(db, job.id, org.id)
        await db.commit()

        # Reload job and findings
        await db.refresh(job)
        findings = (await db.execute(
            select(Finding).where(Finding.job_id == job.id).order_by(Finding.severity.desc())
        )).scalars().all()

        receipts = (await db.execute(
            select(EvidenceReceipt)
            .join(Finding, Finding.id == EvidenceReceipt.finding_id)
            .where(Finding.job_id == job.id)
        )).scalars().all()

        print(f"    Validation Job ID:     {job.id}")
        print(f"    Job Status:            {job.status.value}")
        print(f"    AI Provider Used:      {job.ai_provider_used}")
        print(f"    Fallback Used:         {job.fallback_used}")
        print(f"    Total Findings Count:  {len(findings)}")
        print(f"    Evidence Receipts:     {len(receipts)}")

        print("\n    Findings Summary:")
        for idx, f in enumerate(findings[:5], 1):
            print(f"      {idx}. [{f.severity.value.upper()}] {f.finding_type.value}: {f.description[:70]}...")

        print("\n    Evidence Receipts:")
        for idx, r in enumerate(receipts[:3], 1):
            rule_type = r.receipt_json.get("rule_grounding_type", "unknown")
            verified_by = r.receipt_json.get("verified_by", "unknown")
            quote = r.receipt_json.get("exact_quote", "")
            print(f"      {idx}. [{rule_type}] {verified_by} -> Quote: {quote[:40]}")

        # Assertions
        assert job.status.value == "completed"
        assert len(findings) > 0
        assert len(receipts) > 0
        assert job.ai_provider_used in ("gemini", "mock")

        print(f"\n[4] Fallback behavior confirmation:")
        print(f"    Configured Provider: gemini")
        print(f"    Runtime Provider:   {job.ai_provider_used}")
        print(f"    Per-request Fallback: fallback_used={job.fallback_used}")
        print(f"    [PASS] Phase 4 Live AI & Fallback Verification Complete!")


if __name__ == "__main__":
    import asyncio.runners
    asyncio.runners.run(verify_phase4())
