"""Guideline schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.guideline import RecommendationStatus, SignalSeverity, SignalSourceType


class ReviewSignalCreate(BaseModel):
    item_id: uuid.UUID
    source_type: SignalSourceType
    signal_text: str
    severity: SignalSeverity


class ReviewSignalResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    item_id: uuid.UUID
    source_type: SignalSourceType
    signal_text: str
    severity: SignalSeverity
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewSignalList(BaseModel):
    items: list[ReviewSignalResponse]
    total: int
    page: int
    page_size: int


class AmbiguityAnalysisResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    item_id: uuid.UUID
    trigger_signal_count: int
    analysis_summary: str
    ambiguous_aspects_json: dict
    confidence_score: float
    analyzed_at: datetime
    ai_provider_used: str | None

    model_config = {"from_attributes": True}


class GuidelineRecommendationResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    item_id: uuid.UUID
    analysis_id: uuid.UUID
    proposed_content: str
    rationale: str | None
    status: RecommendationStatus
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GuidelineRecommendationReview(BaseModel):
    status: RecommendationStatus
    review_note: str | None = None


class GuidelineRecommendationList(BaseModel):
    items: list[GuidelineRecommendationResponse]
    total: int
    page: int
    page_size: int
