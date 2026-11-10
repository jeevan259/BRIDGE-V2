"""Knowledge schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.knowledge import IngestionStatus, ItemStatus, ItemType, SourceType


class KnowledgeSourceCreate(BaseModel):
    name: str
    source_type: SourceType
    description: str | None = None


class KnowledgeSourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class KnowledgeSourceResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    source_type: SourceType
    description: str | None
    is_active: bool
    current_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSourceList(BaseModel):
    items: list[KnowledgeSourceResponse]
    total: int
    page: int
    page_size: int


class SourceVersionResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    version_number: int
    file_path: str | None
    file_hash: str | None
    ingestion_status: IngestionStatus
    ingested_at: datetime | None
    is_current: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeItemCreate(BaseModel):
    source_id: uuid.UUID
    item_type: ItemType
    title: str
    content: str


class KnowledgeItemUpdate(BaseModel):
    title: str | None = None
    item_type: ItemType | None = None


class KnowledgeItemResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    source_id: uuid.UUID
    item_type: ItemType
    title: str
    current_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeItemList(BaseModel):
    items: list[KnowledgeItemResponse]
    total: int
    page: int
    page_size: int


class ItemVersionResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    version_number: int
    content: str
    status: ItemStatus
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ItemVersionReview(BaseModel):
    status: ItemStatus
    review_note: str | None = None


class PassageResponse(BaseModel):
    id: uuid.UUID
    version_id: uuid.UUID
    source_id: uuid.UUID
    passage_index: int
    text: str
    char_start: int
    char_end: int

    model_config = {"from_attributes": True}
