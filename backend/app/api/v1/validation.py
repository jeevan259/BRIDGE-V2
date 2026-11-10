"""Validation endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbDep, require_role
from app.models.user import User, UserRole
from app.models.validation import (
    EvidenceReceipt, Finding, FindingCitation, FindingStatus, ValidationJob
)
from app.schemas.validation import (
    CitationResponse, EvidenceReceiptResponse, FindingList, FindingOverride, FindingResponse,
    ValidationJobCreate, ValidationJobList, ValidationJobResponse,
)
from app.services.jobs import enqueue_job

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/jobs", response_model=ValidationJobResponse, status_code=status.HTTP_201_CREATED)
async def submit_validation_job(
    body: ValidationJobCreate,
    db: DbDep,
    current_user: User = Depends(require_role(
        UserRole.administrator, UserRole.brand_manager, UserRole.creator, UserRole.reviewer
    )),
) -> ValidationJobResponse:
    job = ValidationJob(
        org_id=current_user.org_id,
        content_text=body.content_text,
        content_title=body.content_title,
        submitted_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    # Enqueue background job
    await enqueue_job(
        db,
        job_type="validate_content",
        payload={
            "validation_job_id": str(job.id),
            "org_id": str(current_user.org_id),
        },
        org_id=current_user.org_id,
    )

    from app.services.audit import append_audit_event
    await append_audit_event(
        db,
        org_id=current_user.org_id,
        event_type="VALIDATION_JOB_SUBMITTED",
        actor=current_user,
        resource_type="validation_job",
        resource_id=str(job.id),
        diff_json={"content_title": body.content_title},
    )
    return ValidationJobResponse.model_validate(job)


@router.get("/jobs", response_model=ValidationJobList)
async def list_validation_jobs(
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ValidationJobList:
    org_id = current_user.org_id
    total = (await db.execute(
        select(func.count()).select_from(ValidationJob).where(ValidationJob.org_id == org_id)
    )).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        select(ValidationJob)
        .where(ValidationJob.org_id == org_id)
        .order_by(ValidationJob.created_at.desc())
        .offset(offset).limit(page_size)
    )
    jobs = result.scalars().all()
    return ValidationJobList(
        items=[ValidationJobResponse.model_validate(j) for j in jobs],
        total=total, page=page, page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=ValidationJobResponse)
async def get_validation_job(
    job_id: uuid.UUID, db: DbDep, current_user: CurrentUser
) -> ValidationJobResponse:
    result = await db.execute(
        select(ValidationJob).where(
            ValidationJob.id == job_id, ValidationJob.org_id == current_user.org_id
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ValidationJobResponse.model_validate(job)


@router.get("/jobs/{job_id}/findings", response_model=FindingList)
async def list_job_findings(
    job_id: uuid.UUID,
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> FindingList:
    # Quarantined hallucinations (unsupported citations) must NOT appear in normal findings
    base_filter = [
        Finding.job_id == job_id,
        Finding.org_id == current_user.org_id,
        Finding.finding_type != FindingType.unsupported,
        Finding.is_evidence_backed == True,
    ]
    total = (await db.execute(
        select(func.count()).select_from(Finding).where(*base_filter)
    )).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Finding)
        .where(*base_filter)
        .order_by(Finding.severity.desc())
        .offset(offset).limit(page_size)
    )
    findings = result.scalars().all()
    return FindingList(
        items=[FindingResponse.model_validate(f) for f in findings],
        total=total, page=page, page_size=page_size,
    )


@router.get("/jobs/{job_id}/hallucination-defense", response_model=FindingList)
async def list_job_hallucination_defense(
    job_id: uuid.UUID,
    db: DbDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> FindingList:
    """Quarantined AI claims and invalid citations trapped by server-side verification."""
    defense_filter = [
        Finding.job_id == job_id,
        Finding.org_id == current_user.org_id,
        (Finding.finding_type == FindingType.unsupported) | (Finding.is_evidence_backed == False),
    ]
    total = (await db.execute(
        select(func.count()).select_from(Finding).where(*defense_filter)
    )).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Finding)
        .where(*defense_filter)
        .order_by(Finding.severity.desc())
        .offset(offset).limit(page_size)
    )
    findings = result.scalars().all()
    return FindingList(
        items=[FindingResponse.model_validate(f) for f in findings],
        total=total, page=page, page_size=page_size,
    )


@router.get("/hallucination-defense", response_model=FindingList)
async def list_org_hallucination_defense(
    db: DbDep,
    current_user: CurrentUser,
    job_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> FindingList:
    """Organization-wide quarantined hallucinations trap log."""
    defense_filter = [
        Finding.org_id == current_user.org_id,
        (Finding.finding_type == FindingType.unsupported) | (Finding.is_evidence_backed == False),
    ]
    if job_id:
        defense_filter.append(Finding.job_id == job_id)
    total = (await db.execute(
        select(func.count()).select_from(Finding).where(*defense_filter)
    )).scalar_one()
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Finding)
        .where(*defense_filter)
        .order_by(Finding.severity.desc())
        .offset(offset).limit(page_size)
    )
    findings = result.scalars().all()
    return FindingList(
        items=[FindingResponse.model_validate(f) for f in findings],
        total=total, page=page, page_size=page_size,
    )


@router.post("/findings/{finding_id}/override", response_model=FindingResponse)
async def override_finding(
    finding_id: uuid.UUID,
    body: FindingOverride,
    db: DbDep,
    current_user: User = Depends(require_role(
        UserRole.administrator, UserRole.brand_manager, UserRole.reviewer
    )),
) -> FindingResponse:
    from app.services.audit import append_audit_event
    from app.models.guideline import ReviewSignal, SignalSeverity, SignalSourceType
    from app.models.knowledge import ItemVersion

    result = await db.execute(
        select(Finding).where(
            Finding.id == finding_id, Finding.org_id == current_user.org_id
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    old_status = finding.status.value
    finding.status = FindingStatus.overridden
    finding.override_reason_code = body.override_reason_code
    finding.override_reason_text = body.override_reason_text
    finding.overridden_by = current_user.id
    finding.overridden_at = datetime.now(timezone.utc)
    await db.flush()

    # Rule 7: Overrides are audited
    await append_audit_event(
        db,
        org_id=current_user.org_id,
        event_type="FINDING_OVERRIDDEN",
        actor=current_user,
        resource_type="finding",
        resource_id=str(finding.id),
        diff_json={
            "old_status": old_status,
            "new_status": FindingStatus.overridden.value,
            "override_reason_code": body.override_reason_code.value,
            "override_reason_text": body.override_reason_text,
        },
    )

    # GuidelineX linkage: If rule was unclear, create ReviewSignal for ambiguity tracking
    if body.override_reason_code.value == "rule_unclear":
        # Find associated item from citations if available
        cit_res = await db.execute(
            select(FindingCitation).where(FindingCitation.finding_id == finding.id).limit(1)
        )
        citation = cit_res.scalar_one_or_none()
        if citation:
            ver_res = await db.execute(
                select(ItemVersion).where(ItemVersion.id == citation.item_version_id)
            )
            ver = ver_res.scalar_one_or_none()
            if ver:
                signal = ReviewSignal(
                    org_id=current_user.org_id,
                    item_id=ver.item_id,
                    source_type=SignalSourceType.override,
                    signal_text=f"Override on finding {finding.id}: {body.override_reason_text or 'Reviewer flagged rule as unclear'}",
                    severity=SignalSeverity.medium,
                    created_by=current_user.id,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(signal)
                await db.flush()

    return FindingResponse.model_validate(finding)


@router.get("/findings/{finding_id}/citations", response_model=list[CitationResponse])
async def get_finding_citations(
    finding_id: uuid.UUID, db: DbDep, current_user: CurrentUser
) -> list[CitationResponse]:
    result = await db.execute(
        select(FindingCitation).where(FindingCitation.finding_id == finding_id)
    )
    return [CitationResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/findings/{finding_id}/evidence", response_model=list[EvidenceReceiptResponse])
async def get_finding_evidence(
    finding_id: uuid.UUID, db: DbDep, current_user: CurrentUser
) -> list[EvidenceReceiptResponse]:
    result = await db.execute(
        select(EvidenceReceipt).where(EvidenceReceipt.finding_id == finding_id)
    )
    return [EvidenceReceiptResponse.model_validate(r) for r in result.scalars().all()]
