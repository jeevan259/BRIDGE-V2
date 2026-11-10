"""GuidelineX domain models — GuidelineSignal, GuidelineInsight, GuidelineRecommendation."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SignalSourceType(str, enum.Enum):
    override = "override"
    reviewer_comment = "reviewer_comment"
    external_feedback = "external_feedback"


class SignalSeverity(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class RecommendationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ReviewSignal(UUIDMixin, Base):
    __tablename__ = "review_signals"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_type: Mapped[SignalSourceType] = mapped_column(
        Enum(SignalSourceType, name="signal_source_type"), nullable=False
    )
    signal_text: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[SignalSeverity] = mapped_column(
        Enum(SignalSeverity, name="signal_severity"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    item: Mapped["KnowledgeItem"] = relationship("KnowledgeItem")  # type: ignore[name-defined]
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<ReviewSignal id={self.id} item_id={self.item_id}>"


GuidelineSignal = ReviewSignal


class AmbiguityAnalysis(UUIDMixin, Base):
    __tablename__ = "ambiguity_analyses"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trigger_signal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_summary: Mapped[str] = mapped_column(Text, nullable=False)
    ambiguous_aspects_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ai_provider_used: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    item: Mapped["KnowledgeItem"] = relationship("KnowledgeItem")  # type: ignore[name-defined]
    recommendations: Mapped[list["GuidelineRecommendation"]] = relationship(
        "GuidelineRecommendation", back_populates="analysis", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<AmbiguityAnalysis id={self.id} item_id={self.item_id}>"


GuidelineInsight = AmbiguityAnalysis


class GuidelineRecommendation(UUIDMixin, Base):
    __tablename__ = "guideline_recommendations"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ambiguity_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    proposed_content: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, name="recommendation_status"),
        nullable=False,
        default=RecommendationStatus.pending,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    item: Mapped["KnowledgeItem"] = relationship("KnowledgeItem")  # type: ignore[name-defined]
    analysis: Mapped["AmbiguityAnalysis"] = relationship("AmbiguityAnalysis", back_populates="recommendations")
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by])  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<GuidelineRecommendation id={self.id} status={self.status}>"
