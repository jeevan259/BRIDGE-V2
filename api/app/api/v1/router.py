"""v1 router — aggregates all sub-routers + dashboard stats."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep
from app.api.v1 import auth, users, organisations, knowledge, validation, continuity, guideline, audit
from app.models.knowledge import ItemStatus, ItemVersion, KnowledgeItem
from app.models.validation import Finding, FindingStatus
from app.models.continuity import RevalidationStatus, RevalidationTask
from app.models.validation import FindingSeverity

router = APIRouter()

# Mount all sub-routers
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(organisations.router)
router.include_router(knowledge.router)
router.include_router(validation.router)
router.include_router(continuity.router)
router.include_router(guideline.router)
router.include_router(audit.router)


@router.get("/dashboard/stats", tags=["dashboard"])
async def dashboard_stats(
    db: DbDep,
    current_user: CurrentUser,
) -> dict:
    """Real dashboard statistics for the current org."""
    org_id = current_user.org_id

    # Knowledge Items count (approved)
    approved_items = (await db.execute(
        select(func.count()).select_from(ItemVersion)
        .where(ItemVersion.status == ItemStatus.approved)
        .join(KnowledgeItem, KnowledgeItem.id == ItemVersion.item_id)
        .where(KnowledgeItem.org_id == org_id)
    )).scalar_one()

    # Total knowledge items in org
    total_items = (await db.execute(
        select(func.count()).select_from(KnowledgeItem).where(KnowledgeItem.org_id == org_id)
    )).scalar_one()

    # Active findings (pending + confirmed) by severity
    active_findings = (await db.execute(
        select(func.count()).select_from(Finding)
        .where(
            Finding.org_id == org_id,
            Finding.status.in_([FindingStatus.pending, FindingStatus.confirmed]),
        )
    )).scalar_one()

    high_findings = (await db.execute(
        select(func.count()).select_from(Finding)
        .where(
            Finding.org_id == org_id,
            Finding.severity == FindingSeverity.high,
            Finding.status.in_([FindingStatus.pending, FindingStatus.confirmed]),
        )
    )).scalar_one()

    # Pending revalidation tasks
    pending_tasks = (await db.execute(
        select(func.count()).select_from(RevalidationTask)
        .where(
            RevalidationTask.org_id == org_id,
            RevalidationTask.status == RevalidationStatus.pending,
        )
    )).scalar_one()

    # In-progress revalidation tasks
    in_progress_tasks = (await db.execute(
        select(func.count()).select_from(RevalidationTask)
        .where(
            RevalidationTask.org_id == org_id,
            RevalidationTask.status == RevalidationStatus.in_progress,
        )
    )).scalar_one()

    return {
        "knowledge_items": {
            "total": total_items,
            "approved": approved_items,
        },
        "active_findings": {
            "total": active_findings,
            "high_severity": high_findings,
        },
        "pending_tasks": {
            "total": pending_tasks + in_progress_tasks,
            "pending": pending_tasks,
            "in_progress": in_progress_tasks,
        },
        "revalidation_queue": {
            "total": pending_tasks,
        },
    }
