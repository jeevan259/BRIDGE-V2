"""Brand Continuity domain models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class EdgeType(str, enum.Enum):
    confirmed = "confirmed"
    possible = "possible"


class RevalidationPriority(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class RevalidationStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    dismissed = "dismissed"


class DependencyEdge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "dependency_edges"
    __table_args__ = (
        UniqueConstraint("content_identifier", "item_id", name="uq_dep_edge_content_item"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_identifier: Mapped[str] = mapped_column(Text, nullable=False)
    content_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    edge_type: Mapped[EdgeType] = mapped_column(
        Enum(EdgeType, name="edge_type"), nullable=False, default=EdgeType.possible
    )
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    item: Mapped["KnowledgeItem"] = relationship("KnowledgeItem")  # type: ignore[name-defined]
    confirmer: Mapped["User | None"] = relationship("User", foreign_keys=[confirmed_by])  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<DependencyEdge id={self.id} content={self.content_identifier!r}>"


class ChangeEvent(UUIDMixin, Base):
    __tablename__ = "change_events"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="SET NULL"), nullable=True
    )
    new_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    changer: Mapped["User | None"] = relationship("User", foreign_keys=[changed_by])  # type: ignore[name-defined]
    impact_reports: Mapped[list["ImpactReport"]] = relationship(
        "ImpactReport", back_populates="change_event", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<ChangeEvent id={self.id} source_id={self.source_id}>"


class ImpactReport(UUIDMixin, Base):
    __tablename__ = "impact_reports"

    change_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("change_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    affected_content_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blast_radius_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Relationships
    change_event: Mapped["ChangeEvent"] = relationship("ChangeEvent", back_populates="impact_reports")
    revalidation_tasks: Mapped[list["RevalidationTask"]] = relationship(
        "RevalidationTask", back_populates="impact_report", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<ImpactReport id={self.id} blast_radius={self.blast_radius_score}>"


class RevalidationTask(UUIDMixin, Base):
    __tablename__ = "revalidation_tasks"

    impact_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("impact_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_identifier: Mapped[str] = mapped_column(Text, nullable=False)
    content_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    priority: Mapped[RevalidationPriority] = mapped_column(
        Enum(RevalidationPriority, name="revalidation_priority"), nullable=False
    )
    exposure_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[RevalidationStatus] = mapped_column(
        Enum(RevalidationStatus, name="revalidation_status"),
        nullable=False,
        default=RevalidationStatus.pending,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    impact_report: Mapped["ImpactReport"] = relationship("ImpactReport", back_populates="revalidation_tasks")
    assignee: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_to])  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<RevalidationTask id={self.id} content={self.content_identifier!r}>"
