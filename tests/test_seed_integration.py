"""Opt-in integration check for the live Aurora demo seed."""
from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models.continuity import DependencyEdge
from app.models.guideline import ReviewSignal
from app.models.knowledge import KnowledgeItem, Passage
from app.models.organisation import Organisation
from app.models.user import User
from app.models.validation import ValidationJob
from app.services.audit import verify_audit_chain
from app.seed_demo import seed_demo_tenant


@pytest.mark.skipif(
    os.getenv("BRIDGE_RUN_SEED_INTEGRATION") != "1",
    reason="set BRIDGE_RUN_SEED_INTEGRATION=1 to run against the configured Neon database",
)
def test_aurora_seed_counts_and_audit_chain():
    async def run() -> None:
        async with AsyncSessionLocal() as db:
            seed_result = await seed_demo_tenant(db)
            assert seed_result["status"] in {"success", "already_seeded"}
            org = (await db.execute(
                select(Organisation).where(Organisation.slug == "aurora-outdoors")
            )).scalar_one()

            async def count(model) -> int:
                query = select(func.count()).select_from(model)
                if hasattr(model, "org_id"):
                    query = query.where(model.org_id == org.id)
                return (await db.execute(query)).scalar_one()

            assert await count(User) == 5
            assert await count(Passage) >= 25
            assert await count(DependencyEdge) >= 12
            # Live round-trip checks may add jobs after the six seeded examples.
            assert await count(ValidationJob) >= 6
            assert await count(ReviewSignal) >= 20
            assert await count(KnowledgeItem) >= 12
            assert (await verify_audit_chain(db, org.id))["is_valid"] is True

        asyncio.runners.run(run())
