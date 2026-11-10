"""Audit schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    event_type: str
    actor_id: uuid.UUID | None
    actor_email: str
    resource_type: str | None
    resource_id: str | None
    diff_json: dict | None
    prev_hash: str | None
    event_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditEventList(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int


class AuditVerifyResponse(BaseModel):
    is_valid: bool
    total_events: int
    broken_at: uuid.UUID | None = None
    message: str
