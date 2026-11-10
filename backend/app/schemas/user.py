"""User schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.user import UserRole


class UserBase(BaseModel):
    email: str
    full_name: str | None = None
    role: UserRole = UserRole.creator


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    id: uuid.UUID
    org_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserList(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
