"""Brand Continuity endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep, require_role
from app.models.continuity import (
    ChangeEvent, DependencyEdge, EdgeType, ImpactReport, RevalidationTask
)
from app.models.user import User, UserRole
from app.schemas.continuity import (
    ChangeEventResponse, DependencyEdgeCreate, DependencyEdgeList, DependencyEdgeResponse,
    ImpactReportResponse, RevalidationTaskList, RevalidationTaskResponse, RevalidationTaskUpdate,
    SourceChangeRequest,
)

router = APIRouter(prefix="/continuity", tags=["continuity"])


@router.get("/edges", response_model=DependencyEdgeList)
async def list_edges(
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> DependencyEdgeList:
    org_id = current_user.org_id
    total = (await db.execute(
        select(func.count()).select_from(DependencyEdge).where(DependencyEdge.org_id == org_id)
    )).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        select(DependencyEdge)
        .where(DependencyEdge.org_id == org_id)
        .order_by(DependencyEdge.created_at.desc())
        .offset(offset).limit(page_size)
    )
    edges = result.scalars().all()
    return DependencyEdgeList(
        items=[DependencyEdgeResponse.model_validate(e) for e in edges],
        total=total, page=page, page_size=page_size,
    )


@router.post("/edges", response_model=DependencyEdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_edge(
    body: DependencyEdgeCreate,
    db: DbDep,
    current_user: User = Depends(require_role(
        UserRole.administrator, UserRole.brand_manager, UserRole.reviewer
    )),
) -> DependencyEdgeResponse:
    edge = DependencyEdge(
        org_id=current_user.org_id,
        content_identifier=body.content_identifier,
        content_title=body.content_title,
        item_id=body.item_id,
        edge_type=body.edge_type,
        notes=body.notes,
    )
    if body.edge_type == EdgeType.confirmed:
        edge.confirmed_by = current_user.id
        edge.confirmed_at = datetime.now(timezone.utc)
    db.add(edge)
    await db.flush()
    return DependencyEdgeResponse.model_validate(edge)


@router.post("/edges/{edge_id}/confirm", response_model=DependencyEdgeResponse)
async def confirm_edge(
    edge_id: uuid.UUID,
    db: DbDep,
    current_user: User = Depends(require_role(
        UserRole.administrator, UserRole.brand_manager, UserRole.reviewer
    )),
) -> DependencyEdgeResponse:
    result = await db.execute(
        select(DependencyEdge).where(
            DependencyEdge.id == edge_id, DependencyEdge.org_id == current_user.org_id
        )
    )
    edge = result.scalar_one_or_none()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    edge.edge_type = EdgeType.confirmed
    edge.confirmed_by = current_user.id
    edge.confirmed_at = datetime.now(timezone.utc)
    await db.flush()
    return DependencyEdgeResponse.model_validate(edge)


@router.get("/changes", response_model=list[ChangeEventResponse])
async def list_change_events(
    db: DbDep,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
) -> list[ChangeEventResponse]:
    result = await db.execute(
        select(ChangeEvent)
        .where(ChangeEvent.org_id == current_user.org_id)
        .order_by(ChangeEvent.created_at.desc())
        .limit(limit)
    )
    return [ChangeEventResponse.model_validate(e) for e in result.scalars().all()]


@router.post("/simulate-change", status_code=status.HTTP_201_CREATED)
async def simulate_source_change(
    body: SourceChangeRequest,
    db: DbDep,
    current_user: User = Depends(require_role(
        UserRole.administrator, UserRole.brand_manager
    )),
) -> dict:
    """Execute Rule 6: Simulate a live brand specification update in a single transaction."""
    from app.services.continuity import trigger_source_version_change
    from app.models.knowledge import KnowledgeSource

    target_source_id = body.source_id
    if not target_source_id:
        src_res = await db.execute(
            select(KnowledgeSource)
            .where(KnowledgeSource.org_id == current_user.org_id)
            .order_by(KnowledgeSource.created_at.desc())
            .limit(1)
        )
        src = src_res.scalar_one_or_none()
        if not src:
            raise HTTPException(status_code=404, detail="No knowledge source found in organization to simulate change")
        target_source_id = src.id

    result = await trigger_source_version_change(
        db,
        source_id=target_source_id,
        org_id=current_user.org_id,
        actor=current_user,
        change_summary=body.change_summary,
        new_content_text=body.new_content_text,
    )
    return result



@router.get("/impact-reports/{report_id}", response_model=ImpactReportResponse)
async def get_impact_report(
    report_id: uuid.UUID, db: DbDep, current_user: CurrentUser
) -> ImpactReportResponse:
    result = await db.execute(
        select(ImpactReport).where(
            ImpactReport.id == report_id, ImpactReport.org_id == current_user.org_id
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Impact report not found")
    return ImpactReportResponse.model_validate(report)


@router.get("/revalidation-tasks", response_model=RevalidationTaskList)
async def list_revalidation_tasks(
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> RevalidationTaskList:
    org_id = current_user.org_id
    total = (await db.execute(
        select(func.count()).select_from(RevalidationTask).where(RevalidationTask.org_id == org_id)
    )).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        select(RevalidationTask)
        .where(RevalidationTask.org_id == org_id)
        .order_by(RevalidationTask.created_at.desc())
        .offset(offset).limit(page_size)
    )
    tasks = result.scalars().all()
    return RevalidationTaskList(
        items=[RevalidationTaskResponse.model_validate(t) for t in tasks],
        total=total, page=page, page_size=page_size,
    )


@router.patch("/revalidation-tasks/{task_id}", response_model=RevalidationTaskResponse)
async def update_revalidation_task(
    task_id: uuid.UUID,
    body: RevalidationTaskUpdate,
    db: DbDep,
    current_user: User = Depends(require_role(
        UserRole.administrator, UserRole.brand_manager, UserRole.reviewer
    )),
) -> RevalidationTaskResponse:
    result = await db.execute(
        select(RevalidationTask).where(
            RevalidationTask.id == task_id, RevalidationTask.org_id == current_user.org_id
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if body.status is not None:
        task.status = body.status
        if body.status.value == "completed":
            task.completed_at = datetime.now(timezone.utc)
    if body.assigned_to is not None:
        task.assigned_to = body.assigned_to
    await db.flush()
    return RevalidationTaskResponse.model_validate(task)
