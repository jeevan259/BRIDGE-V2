"""Continuity schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.continuity import EdgeType, RevalidationPriority, RevalidationStatus


class DependencyEdgeCreate(BaseModel):
    content_identifier: str
    content_title: str | None = None
    item_id: uuid.UUID
    edge_type: EdgeType = EdgeType.possible
    notes: str | None = None


class DependencyEdgeResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    content_identifier: str
    content_title: str | None
    item_id: uuid.UUID
    edge_type: EdgeType
    confirmed_by: uuid.UUID | None
    confirmed_at: datetime | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DependencyEdgeList(BaseModel):
    items: list[DependencyEdgeResponse]
    total: int
    page: int
    page_size: int


class ChangeEventResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    source_id: uuid.UUID
    old_version_id: uuid.UUID | None
    new_version_id: uuid.UUID
    changed_by: uuid.UUID | None
    change_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ImpactReportResponse(BaseModel):
    id: uuid.UUID
    change_event_id: uuid.UUID
    org_id: uuid.UUID
    affected_content_count: int
    blast_radius_score: float
    generated_at: datetime
    report_json: dict

    model_config = {"from_attributes": True}


class RevalidationTaskResponse(BaseModel):
    id: uuid.UUID
    impact_report_id: uuid.UUID
    org_id: uuid.UUID
    content_identifier: str
    content_title: str | None
    priority: RevalidationPriority
    exposure_score: float
    status: RevalidationStatus
    assigned_to: uuid.UUID | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class RevalidationTaskList(BaseModel):
    items: list[RevalidationTaskResponse]
    total: int
    page: int
    page_size: int


class RevalidationTaskUpdate(BaseModel):
    status: RevalidationStatus | None = None
    assigned_to: uuid.UUID | None = None


class SourceChangeRequest(BaseModel):
    source_id: uuid.UUID | None = None
    rule_name: str | None = None
    change_summary: str = "Updated clearspace requirements to 40px minimum padding"
    new_content_text: str | None = None
    dry_run: bool = False


class ChangeSimulationResponse(BaseModel):
    simulation: bool = True
    rule_name: str
    change_summary: str
    impacted_guidelines_count: int
    impacted_guidelines: list[str]
    impacted_assets_count: int
    impacted_assets: list[str]
    blast_radius_score: float
    revalidation_queued: bool = False
    message: str


class ChangeApplyResponse(BaseModel):
    applied: bool = True
    change_event_id: uuid.UUID
    impact_report_id: uuid.UUID
    rule_name: str
    change_summary: str
    impacted_guidelines_count: int
    impacted_guidelines: list[str]
    impacted_assets_count: int
    impacted_assets: list[str]
    blast_radius_score: float
    tasks_enqueued: int
    revalidation_queued: bool = True
    message: str

