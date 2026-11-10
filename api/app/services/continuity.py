"""Brand Continuity Service — source change events, blast radius calculation, and revalidation tasks."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.continuity import (
    ChangeEvent,
    DependencyEdge,
    EdgeType,
    ImpactReport,
    RevalidationPriority,
    RevalidationStatus,
    RevalidationTask,
)
from app.models.knowledge import KnowledgeItem, KnowledgeSource, SourceVersion
from app.models.user import User
from app.services.audit import append_audit_event

logger = logging.getLogger(__name__)


async def trigger_source_version_change(
    db: AsyncSession,
    *,
    source_id: uuid.UUID,
    org_id: uuid.UUID,
    actor: User,
    change_summary: str,
    new_content_text: str | None = None,
) -> dict[str, Any]:
    """Execute Rule 6: A source change creates a new version, a ChangeEvent,

    an impact report and revalidation tasks — in one transaction.
    """
    # 1. Fetch Source
    source_res = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id,
            KnowledgeSource.org_id == org_id,
        )
    )
    source = source_res.scalar_one_or_none()
    if not source:
        raise ValueError(f"KnowledgeSource {source_id} not found")

    # 2. Fetch current version
    old_version_res = await db.execute(
        select(SourceVersion).where(
            SourceVersion.source_id == source_id,
            SourceVersion.is_current.is_(True),
        )
    )
    old_version = old_version_res.scalar_one_or_none()

    old_version_id = old_version.id if old_version else None
    next_ver_num = (old_version.version_number + 1) if old_version else 1
    content_text = new_content_text or (old_version.content_text if old_version else "")

    # Supersede old version
    if old_version:
        old_version.is_current = False
        await db.flush()

    # 3. Create new SourceVersion
    new_version = SourceVersion(
        source_id=source_id,
        version_number=next_ver_num,
        content_text=content_text,
        is_current=True,
        created_by=actor.id,
        ingested_at=datetime.now(timezone.utc),
    )
    db.add(new_version)
    await db.flush()

    source.current_version_id = new_version.id
    await db.flush()

    # 4. Create ChangeEvent
    change_event = ChangeEvent(
        org_id=org_id,
        source_id=source_id,
        old_version_id=old_version_id,
        new_version_id=new_version.id,
        changed_by=actor.id,
        change_summary=change_summary,
        created_at=datetime.now(timezone.utc),
    )
    db.add(change_event)
    await db.flush()

    # 5. Query all governed items tied to this source
    items_res = await db.execute(
        select(KnowledgeItem).where(
            KnowledgeItem.source_id == source_id,
            KnowledgeItem.org_id == org_id,
        )
    )
    items = items_res.scalars().all()
    item_ids = [item.id for item in items]

    # 6. Query all dependency edges connected to these items
    edges: list[DependencyEdge] = []
    if item_ids:
        edges_res = await db.execute(
            select(DependencyEdge).where(
                DependencyEdge.item_id.in_(item_ids),
                DependencyEdge.org_id == org_id,
            )
        )
        edges = list(edges_res.scalars().all())

    confirmed_edges = [e for e in edges if e.edge_type == EdgeType.confirmed]
    possible_edges = [e for e in edges if e.edge_type == EdgeType.possible]

    # Calculate Blast Radius Score
    # Confirmed edge has 35.0 weight, possible edge has 15.0 weight, base scale to 100
    raw_score = len(confirmed_edges) * 35.0 + len(possible_edges) * 15.0
    blast_radius_score = min(100.0, max(15.0 if edges else 0.0, round(raw_score, 1)))

    report_payload = {
        "source_id": str(source_id),
        "source_name": source.name,
        "old_version_number": old_version.version_number if old_version else None,
        "new_version_number": next_ver_num,
        "affected_items_count": len(items),
        "total_dependency_edges": len(edges),
        "confirmed_edges_count": len(confirmed_edges),
        "possible_edges_count": len(possible_edges),
        "change_summary": change_summary,
        "blast_radius_score": blast_radius_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 7. Create ImpactReport
    impact_report = ImpactReport(
        change_event_id=change_event.id,
        org_id=org_id,
        affected_content_count=len(edges),
        blast_radius_score=blast_radius_score,
        generated_at=datetime.now(timezone.utc),
        report_json=report_payload,
    )
    db.add(impact_report)
    await db.flush()

    # 8. Create RevalidationTasks for affected content assets
    enqueued_tasks: list[RevalidationTask] = []
    # Deduplicate by content_identifier
    seen_identifiers: set[str] = set()
    for edge in edges:
        if edge.content_identifier in seen_identifiers:
            continue
        seen_identifiers.add(edge.content_identifier)

        priority = (
            RevalidationPriority.high
            if edge.edge_type == EdgeType.confirmed
            else RevalidationPriority.medium
        )
        exposure_score = 95.0 if edge.edge_type == EdgeType.confirmed else 60.0

        task = RevalidationTask(
            impact_report_id=impact_report.id,
            org_id=org_id,
            content_identifier=edge.content_identifier,
            content_title=edge.content_title or edge.content_identifier.split("//")[-1],
            priority=priority,
            exposure_score=exposure_score,
            status=RevalidationStatus.pending,
            created_at=datetime.now(timezone.utc),
        )
        db.add(task)
        enqueued_tasks.append(task)

    await db.flush()

    # 9. Append Cryptographic Audit Event
    await append_audit_event(
        db,
        org_id=org_id,
        event_type="SOURCE_VERSION_CHANGED",
        actor=actor,
        resource_type="knowledge_source",
        resource_id=str(source_id),
        diff_json={
            "change_event_id": str(change_event.id),
            "impact_report_id": str(impact_report.id),
            "old_version_number": old_version.version_number if old_version else None,
            "new_version_number": next_ver_num,
            "blast_radius_score": blast_radius_score,
            "enqueued_tasks_count": len(enqueued_tasks),
        },
    )

    return {
        "change_event_id": str(change_event.id),
        "impact_report_id": str(impact_report.id),
        "blast_radius_score": blast_radius_score,
        "affected_content_count": len(edges),
        "tasks_enqueued": len(enqueued_tasks),
    }

