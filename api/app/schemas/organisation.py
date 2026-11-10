"""Organisation schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class OrganisationBase(BaseModel):
    name: str
    slug: str


class OrganisationCreate(OrganisationBase):
    pass


class OrganisationUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class OrganisationResponse(OrganisationBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganisationList(BaseModel):
    items: list[OrganisationResponse]
    total: int
    page: int
    page_size: int
