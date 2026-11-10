import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import AsyncSessionLocal
from app.models.organisation import Organisation
from app.models.user import User
from app.models.knowledge import Passage, KnowledgeItem
from app.models.continuity import DependencyEdge
from app.models.validation import ContentItem, ValidationJob
from app.models.guideline import ReviewSignal
from sqlalchemy import func, select

async def main():
    async with AsyncSessionLocal() as session:
        org = (await session.execute(select(Organisation).where(Organisation.slug == "aurora-outdoors"))).scalar_one_or_none()
        if not org:
            print("No Aurora Outdoors org found")
            return
        
        async def c(model):
            q = select(func.count()).select_from(model)
            if hasattr(model, "org_id"):
                q = q.where(model.org_id == org.id)
            return (await session.execute(q)).scalar_one()

        print("Current Neon row counts:")
        print("  Users:", await c(User))
        print("  Passages:", await c(Passage))
        print("  KnowledgeItems:", await c(KnowledgeItem))
        print("  DependencyEdges:", await c(DependencyEdge))
        print("  ContentItems (assets):", await c(ContentItem))
        print("  ValidationJobs:", await c(ValidationJob))
        print("  ReviewSignals:", await c(ReviewSignal))

if __name__ == "__main__":
    asyncio.run(main())
