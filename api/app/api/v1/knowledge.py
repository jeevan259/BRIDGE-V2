"""Knowledge endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbDep, require_role
from app.models.knowledge import (
    ItemStatus, ItemVersion, KnowledgeItem, KnowledgeSource, Passage, SourceVersion
)
from app.models.user import User, UserRole
from app.schemas.knowledge import (
    ItemVersionResponse, ItemVersionReview, KnowledgeItemCreate, KnowledgeItemList,
    KnowledgeItemResponse, KnowledgeItemUpdate, KnowledgeSourceCreate, KnowledgeSourceList,
    KnowledgeSourceResponse, KnowledgeSourceUpdate, PassageResponse, SourceVersionResponse,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ─── Knowledge Sources ───────────────────────────────────────────────────────

@router.get("/sources", response_model=KnowledgeSourceList)
async def list_sources(
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> KnowledgeSourceList:
    org_id = current_user.org_id
    total = (await db.execute(
        select(func.count()).select_from(KnowledgeSource).where(KnowledgeSource.org_id == org_id)
    )).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        select(KnowledgeSource)
        .where(KnowledgeSource.org_id == org_id)
        .order_by(KnowledgeSource.created_at.desc())
        .offset(offset).limit(page_size)
    )
    sources = result.scalars().all()
    return KnowledgeSourceList(
        items=[KnowledgeSourceResponse.model_validate(s) for s in sources],
        total=total, page=page, page_size=page_size,
    )


@router.post("/sources", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    body: KnowledgeSourceCreate,
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator, UserRole.brand_manager)),
) -> KnowledgeSourceResponse:
    source = KnowledgeSource(
        org_id=current_user.org_id,
        name=body.name,
        source_type=body.source_type,
        description=body.description,
    )
    db.add(source)
    await db.flush()
    return KnowledgeSourceResponse.model_validate(source)


@router.get("/sources/{source_id}", response_model=KnowledgeSourceResponse)
async def get_source(
    source_id: uuid.UUID, db: DbDep, current_user: CurrentUser
) -> KnowledgeSourceResponse:
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id, KnowledgeSource.org_id == current_user.org_id
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return KnowledgeSourceResponse.model_validate(source)


@router.patch("/sources/{source_id}", response_model=KnowledgeSourceResponse)
async def update_source(
    source_id: uuid.UUID,
    body: KnowledgeSourceUpdate,
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator, UserRole.brand_manager)),
) -> KnowledgeSourceResponse:
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == source_id, KnowledgeSource.org_id == current_user.org_id
        )
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if body.name is not None:
        source.name = body.name
    if body.description is not None:
        source.description = body.description
    if body.is_active is not None:
        source.is_active = body.is_active
    await db.flush()
    return KnowledgeSourceResponse.model_validate(source)


# ─── Knowledge Items ──────────────────────────────────────────────────────────

@router.get("/items", response_model=KnowledgeItemList)
async def list_items(
    db: DbDep,
    current_user: CurrentUser,
    source_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> KnowledgeItemList:
    org_id = current_user.org_id
    base = select(KnowledgeItem).where(KnowledgeItem.org_id == org_id)
    count_base = select(func.count()).select_from(KnowledgeItem).where(KnowledgeItem.org_id == org_id)
    if source_id:
        base = base.where(KnowledgeItem.source_id == source_id)
        count_base = count_base.where(KnowledgeItem.source_id == source_id)

    total = (await db.execute(count_base)).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        base.order_by(KnowledgeItem.created_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()
    return KnowledgeItemList(
        items=[KnowledgeItemResponse.model_validate(i) for i in items],
        total=total, page=page, page_size=page_size,
    )


@router.post("/items", response_model=KnowledgeItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: KnowledgeItemCreate,
    db: DbDep,
    current_user: User = Depends(require_role(
        UserRole.administrator, UserRole.brand_manager
    )),
) -> KnowledgeItemResponse:
    # Verify source belongs to org
    source_result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.id == body.source_id, KnowledgeSource.org_id == current_user.org_id
        )
    )
    if not source_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Source not found")

    item = KnowledgeItem(
        org_id=current_user.org_id,
        source_id=body.source_id,
        item_type=body.item_type,
        title=body.title,
        created_by=current_user.id,
    )
    db.add(item)
    await db.flush()

    # Create initial version
    version = ItemVersion(
        item_id=item.id,
        version_number=1,
        content=body.content,
        status=ItemStatus.pending,
        created_by=current_user.id,
    )
    db.add(version)
    await db.flush()
    item.current_version_id = version.id
    await db.flush()

    return KnowledgeItemResponse.model_validate(item)


@router.get("/items/{item_id}", response_model=KnowledgeItemResponse)
async def get_item(
    item_id: uuid.UUID, db: DbDep, current_user: CurrentUser
) -> KnowledgeItemResponse:
    result = await db.execute(
        select(KnowledgeItem).where(
            KnowledgeItem.id == item_id, KnowledgeItem.org_id == current_user.org_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return KnowledgeItemResponse.model_validate(item)


@router.get("/items/{item_id}/versions", response_model=list[ItemVersionResponse])
async def list_item_versions(
    item_id: uuid.UUID, db: DbDep, current_user: CurrentUser
) -> list[ItemVersionResponse]:
    result = await db.execute(
        select(ItemVersion)
        .where(ItemVersion.item_id == item_id)
        .order_by(ItemVersion.version_number.desc())
    )
    versions = result.scalars().all()
    return [ItemVersionResponse.model_validate(v) for v in versions]


@router.post(
    "/items/{item_id}/versions/{version_id}/review",
    response_model=ItemVersionResponse,
)
async def review_item_version(
    item_id: uuid.UUID,
    version_id: uuid.UUID,
    body: ItemVersionReview,
    db: DbDep,
    current_user: User = Depends(require_role(UserRole.administrator, UserRole.brand_manager)),
) -> ItemVersionResponse:
    from datetime import datetime, timezone
    from app.services.audit import append_audit_event

    result = await db.execute(
        select(ItemVersion).where(
            ItemVersion.id == version_id, ItemVersion.item_id == item_id
        )
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    old_status = version.status.value

    # Rule 2: At most one current approved version per record.
    # Approving supersedes (never deletes) the previous approved version.
    if body.status == ItemStatus.approved:
        # Supersede any currently approved versions
        prev_approved_res = await db.execute(
            select(ItemVersion).where(
                ItemVersion.item_id == item_id,
                ItemVersion.status == ItemStatus.approved,
                ItemVersion.id != version_id,
            )
        )
        for prev in prev_approved_res.scalars().all():
            prev.status = ItemStatus.superseded

        # Point item's current version to this approved version
        item_res = await db.execute(
            select(KnowledgeItem).where(KnowledgeItem.id == item_id)
        )
        item = item_res.scalar_one_or_none()
        if item:
            item.current_version_id = version.id

    version.status = body.status
    version.review_note = body.review_note
    version.reviewed_by = current_user.id
    version.reviewed_at = datetime.now(timezone.utc)
    await db.flush()

    await append_audit_event(
        db,
        org_id=current_user.org_id,
        event_type="ITEM_VERSION_REVIEWED",
        actor=current_user,
        resource_type="item_version",
        resource_id=str(version.id),
        diff_json={
            "item_id": str(item_id),
            "old_status": old_status,
            "new_status": body.status.value,
            "review_note": body.review_note,
        },
    )

    return ItemVersionResponse.model_validate(version)


@router.get("/passages", response_model=list[PassageResponse])
async def list_passages(
    db: DbDep,
    current_user: CurrentUser,
    source_id: uuid.UUID | None = Query(None),
    version_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> list[PassageResponse]:
    base = select(Passage).where(Passage.org_id == current_user.org_id)
    if source_id:
        base = base.where(Passage.source_id == source_id)
    if version_id:
        base = base.where(Passage.version_id == version_id)
    result = await db.execute(base.order_by(Passage.passage_index.asc()).limit(limit))
    return [PassageResponse.model_validate(p) for p in result.scalars().all()]
