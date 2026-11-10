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
    valid: bool | None = None
    total_events: int
    checked_count: int | None = None
    first_broken_seq: int | None = None
    broken_at: uuid.UUID | None = None
    message: str

    def model_post_init(self, __context: object) -> None:
        if self.valid is None:
            self.valid = self.is_valid
        if self.checked_count is None:
            self.checked_count = self.total_events
