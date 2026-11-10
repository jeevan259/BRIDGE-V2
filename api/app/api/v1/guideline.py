"""GuidelineX endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep, require_role
from app.models.guideline import (
    AmbiguityAnalysis, GuidelineRecommendation, ReviewSignal
)
from app.models.user import User, UserRole
from app.schemas.guideline import (
    AmbiguityAnalysisResponse, GuidelineRecommendationList, GuidelineRecommendationResponse,
    GuidelineRecommendationReview, ReviewSignalCreate, ReviewSignalList, ReviewSignalResponse,
)

router = APIRouter(prefix="/guidelines", tags=["guidelines"])


@router.post("/signals", response_model=ReviewSignalResponse, status_code=status.HTTP_201_CREATED)
async def create_review_signal(
    body: ReviewSignalCreate,
    db: DbDep,
    current_user: User = Depends(require_role(
        UserRole.administrator, UserRole.brand_manager, UserRole.reviewer
    )),
) -> ReviewSignalResponse:
    signal = ReviewSignal(
        org_id=current_user.org_id,
        item_id=body.item_id,
        source_type=body.source_type,
        signal_text=body.signal_text,
        severity=body.severity,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(signal)
    await db.flush()
    return ReviewSignalResponse.model_validate(signal)


@router.get("/signals", response_model=ReviewSignalList)
async def list_review_signals(
    db: DbDep,
    current_user: CurrentUser,
    item_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ReviewSignalList:
    org_id = current_user.org_id
    base = select(ReviewSignal).where(ReviewSignal.org_id == org_id)
    count_base = select(func.count()).select_from(ReviewSignal).where(ReviewSignal.org_id == org_id)
    if item_id:
        base = base.where(ReviewSignal.item_id == item_id)
        count_base = count_base.where(ReviewSignal.item_id == item_id)
    total = (await db.execute(count_base)).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(ReviewSignal.created_at.desc()).offset(offset).limit(page_size)
    )
    return ReviewSignalList(
        items=[ReviewSignalResponse.model_validate(s) for s in result.scalars().all()],
        total=total, page=page, page_size=page_size,
    )


@router.get("/analyses", response_model=list[AmbiguityAnalysisResponse])
async def list_analyses(
    db: DbDep,
    current_user: CurrentUser,
    item_id: uuid.UUID | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> list[AmbiguityAnalysisResponse]:
    base = select(AmbiguityAnalysis).where(AmbiguityAnalysis.org_id == current_user.org_id)
    if item_id:
        base = base.where(AmbiguityAnalysis.item_id == item_id)
    result = await db.execute(base.order_by(AmbiguityAnalysis.analyzed_at.desc()).limit(limit))
    return [AmbiguityAnalysisResponse.model_validate(a) for a in result.scalars().all()]


@router.get("/recommendations", response_model=GuidelineRecommendationList)
async def list_recommendations(
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> GuidelineRecommendationList:
    org_id = current_user.org_id
    total = (await db.execute(
        select(func.count()).select_from(GuidelineRecommendation).where(
            GuidelineRecommendation.org_id == org_id
        )
    )).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        select(GuidelineRecommendation)
        .where(GuidelineRecommendation.org_id == org_id)
        .order_by(GuidelineRecommendation.created_at.desc())
        .offset(offset).limit(page_size)
    )
    recs = result.scalars().all()
    return GuidelineRecommendationList(
        items=[GuidelineRecommendationResponse.model_validate(r) for r in recs],
        total=total, page=page, page_size=page_size,
    )


@router.post(
    "/recommendations/{rec_id}/review",
    response_model=GuidelineRecommendationResponse,
)
async def review_recommendation(
    rec_id: uuid.UUID,
    body: GuidelineRecommendationReview,
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator, UserRole.brand_manager)),
) -> GuidelineRecommendationResponse:
    from app.services.audit import append_audit_event
    from app.models.knowledge import ItemStatus, ItemVersion, KnowledgeItem
    from app.models.continuity import (
        ChangeEvent, DependencyEdge, EdgeType, ImpactReport,
        RevalidationPriority, RevalidationStatus, RevalidationTask,
    )
    from app.models.guideline import RecommendationStatus

    result = await db.execute(
        select(GuidelineRecommendation).where(
            GuidelineRecommendation.id == rec_id,
            GuidelineRecommendation.org_id == current_user.org_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    old_rec_status = rec.status.value
    rec.status = body.status
    rec.review_note = body.review_note
    rec.reviewed_by = current_user.id
    rec.reviewed_at = datetime.now(timezone.utc)
    await db.flush()

    # Rule 8: A guideline recommendation never edits a guideline directly.
    # Admin approval creates a new version and triggers Continuity in one transaction.
    if body.status == RecommendationStatus.approved:
        # 1. Fetch target KnowledgeItem
        item_res = await db.execute(
            select(KnowledgeItem).where(
                KnowledgeItem.id == rec.item_id,
                KnowledgeItem.org_id == current_user.org_id,
            )
        )
        item = item_res.scalar_one()

        # 2. Get highest version number for this item
        max_ver_res = await db.execute(
            select(func.coalesce(func.max(ItemVersion.version_number), 0))
            .where(ItemVersion.item_id == item.id)
        )
        highest_ver_num = max_ver_res.scalar_one()

        # 3. Supersede any currently approved version
        await db.execute(
            update(ItemVersion)
            .where(
                ItemVersion.item_id == item.id,
                ItemVersion.status == ItemStatus.approved,
            )
            .values(status=ItemStatus.superseded)
        )
        await db.flush()

        # 4. Create new approved ItemVersion
        new_item_ver = ItemVersion(
            item_id=item.id,
            version_number=highest_ver_num + 1,
            content=rec.proposed_content,
            status=ItemStatus.approved,
            reviewed_by=current_user.id,
            reviewed_at=datetime.now(timezone.utc),
            review_note=f"Approved GuidelineX recommendation: {body.review_note or 'Adopted advisory amendment'}",
            created_by=current_user.id,
        )
        db.add(new_item_ver)
        await db.flush()

        item.current_version_id = new_item_ver.id
        await db.flush()

        # 5. Trigger Brand Continuity for all assets depending on this guideline
        edges_res = await db.execute(
            select(DependencyEdge).where(
                DependencyEdge.item_id == item.id,
                DependencyEdge.org_id == current_user.org_id,
            )
        )
        edges = list(edges_res.scalars().all())

        if edges:
            confirmed_cnt = sum(1 for e in edges if e.edge_type == EdgeType.confirmed)
            possible_cnt = sum(1 for e in edges if e.edge_type == EdgeType.possible)
            score = min(100.0, round(confirmed_cnt * 35.0 + possible_cnt * 15.0, 1))

            # Fetch source current version
            from app.models.knowledge import KnowledgeSource
            src_res = await db.execute(
                select(KnowledgeSource).where(KnowledgeSource.id == item.source_id)
            )
            src = src_res.scalar_one_or_none()
            cur_ver_id = src.current_version_id if src else None

            change_event = ChangeEvent(
                org_id=current_user.org_id,
                source_id=item.source_id,
                old_version_id=cur_ver_id,
                new_version_id=cur_ver_id or new_item_ver.id,
                changed_by=current_user.id,
                change_summary=f"Guideline update: '{item.title}' v{new_item_ver.version_number} approved via GuidelineX",
                created_at=datetime.now(timezone.utc),
            )
            db.add(change_event)
            await db.flush()

            impact_report = ImpactReport(
                change_event_id=change_event.id,
                org_id=current_user.org_id,
                affected_content_count=len(edges),
                blast_radius_score=score,
                generated_at=datetime.now(timezone.utc),
                report_json={
                    "item_id": str(item.id),
                    "item_title": item.title,
                    "new_version": new_item_ver.version_number,
                    "affected_assets": len(edges),
                    "score": score,
                },
            )
            db.add(impact_report)
            await db.flush()

            for edge in edges:
                task = RevalidationTask(
                    impact_report_id=impact_report.id,
                    org_id=current_user.org_id,
                    content_identifier=edge.content_identifier,
                    content_title=edge.content_title or edge.content_identifier.split("//")[-1],
                    priority=RevalidationPriority.high if edge.edge_type == EdgeType.confirmed else RevalidationPriority.medium,
                    exposure_score=95.0 if edge.edge_type == EdgeType.confirmed else 60.0,
                    status=RevalidationStatus.pending,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(task)
            await db.flush()

    # Cryptographic audit logging
    await append_audit_event(
        db,
        org_id=current_user.org_id,
        event_type="GUIDELINE_RECOMMENDATION_REVIEWED",
        actor=current_user,
        resource_type="guideline_recommendation",
        resource_id=str(rec.id),
        diff_json={
            "old_status": old_rec_status,
            "new_status": rec.status.value,
            "review_note": rec.review_note,
        },
    )

    return GuidelineRecommendationResponse.model_validate(rec)

