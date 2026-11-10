"""Validation schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.validation import (
    FindingSeverity, FindingStatus, FindingType, JobStatus, OverrideReasonCode
)


class ValidationJobCreate(BaseModel):
    content_text: str
    content_title: str | None = None


class ValidationJobResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    content_title: str | None
    status: JobStatus
    ai_provider_used: str | None
    fallback_used: bool
    created_at: datetime
    completed_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class ValidationJobList(BaseModel):
    items: list[ValidationJobResponse]
    total: int
    page: int
    page_size: int


class FindingResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    org_id: uuid.UUID
    finding_type: FindingType
    severity: FindingSeverity
    description: str
    is_evidence_backed: bool
    status: FindingStatus
    override_reason_code: OverrideReasonCode | None
    override_reason_text: str | None
    overridden_by: uuid.UUID | None
    overridden_at: datetime | None

    model_config = {"from_attributes": True}


class FindingList(BaseModel):
    items: list[FindingResponse]
    total: int
    page: int
    page_size: int


class FindingOverride(BaseModel):
    override_reason_code: OverrideReasonCode
    override_reason_text: str | None = None


class CitationResponse(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    item_version_id: uuid.UUID
    passage_id: uuid.UUID | None
    exact_quote: str
    passage_text_at_citation: str

    model_config = {"from_attributes": True}


class EvidenceReceiptResponse(BaseModel):
    id: uuid.UUID
    finding_id: uuid.UUID
    generated_at: datetime
    receipt_json: dict

    model_config = {"from_attributes": True}
