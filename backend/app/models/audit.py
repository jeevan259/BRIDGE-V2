"""Audit log model — append-only, hash-chained."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AuditEvent(Base):
    """
    Append-only audit log with SHA-256 hash chain.
    Each event includes prev_hash and event_hash to form a tamper-evident chain.
    NO update or delete operations permitted.
    """
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_email: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    diff_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), default="success", nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    actor: Mapped["User | None"] = relationship("User", foreign_keys=[actor_id])  # type: ignore[name-defined]

    @property
    def action(self) -> str:
        return self.event_type

    def __repr__(self) -> str:
        return f"<AuditEvent id={self.id} type={self.event_type!r} hash={self.event_hash[:8]}>"
