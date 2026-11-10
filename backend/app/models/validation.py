"""Validation domain models — ContentItem, ContentSnapshot, ValidationRun, Finding, FindingEvidence, ReviewDecision."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class FindingType(str, enum.Enum):
    brand_violation = "brand_violation"
    tone_issue = "tone_issue"
    factual_claim = "factual_claim"
    guideline_breach = "guideline_breach"
    unsupported = "unsupported"


class FindingSeverity(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class FindingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    overridden = "overridden"
    dismissed = "dismissed"


class OverrideReasonCode(str, enum.Enum):
    rule_unclear = "rule_unclear"
    context_exception = "context_exception"
    finding_incorrect = "finding_incorrect"
    source_not_relevant = "source_not_relevant"
    content_corrected = "content_corrected"
    other = "other"


class ContentItem(UUIDMixin, TimestampMixin, Base):
    """Digital asset tracked for brand compliance."""
    __tablename__ = "content_items"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_identifier: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    channel: Mapped[str | None] = mapped_column(String(100), nullable=True)  # web, social, press, ad
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    snapshots: Mapped[list["ContentSnapshot"]] = relationship(
        "ContentSnapshot", back_populates="content_item", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<ContentItem id={self.id} title={self.title!r}>"


class ContentSnapshot(UUIDMixin, Base):
    """Immutable versioned text/asset snapshot submitted for verification."""
    __tablename__ = "content_snapshots"

    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    content_item: Mapped["ContentItem"] = relationship("ContentItem", back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<ContentSnapshot id={self.id} content_id={self.content_id} v={self.snapshot_version}>"


class ValidationJob(UUIDMixin, Base):
    """A single deterministic + AI validation run against brand rules."""
    __tablename__ = "validation_jobs"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_snapshots.id", ondelete="SET NULL"), nullable=True
    )
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), nullable=False, default=JobStatus.pending
    )
    ai_provider_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    rule_set_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    submitter: Mapped["User | None"] = relationship("User", foreign_keys=[submitted_by])  # type: ignore[name-defined]
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="job", lazy="select")

    def __repr__(self) -> str:
        return f"<ValidationJob id={self.id} status={self.status}>"


ValidationRun = ValidationJob


class Finding(UUIDMixin, Base):
    __tablename__ = "findings"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("validation_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finding_type: Mapped[FindingType] = mapped_column(
        Enum(FindingType, name="finding_type"), nullable=False
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="finding_severity"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_evidence_backed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus, name="finding_status"), nullable=False, default=FindingStatus.pending
    )
    override_reason_code: Mapped[OverrideReasonCode | None] = mapped_column(
        Enum(OverrideReasonCode, name="override_reason_code"), nullable=True
    )
    override_reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    overridden_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    overridden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    job: Mapped["ValidationJob"] = relationship("ValidationJob", back_populates="findings")
    overrider: Mapped["User | None"] = relationship("User", foreign_keys=[overridden_by])  # type: ignore[name-defined]
    citations: Mapped[list["FindingCitation"]] = relationship(
        "FindingCitation", back_populates="finding", lazy="select"
    )
    evidence_receipts: Mapped[list["EvidenceReceipt"]] = relationship(
        "EvidenceReceipt", back_populates="finding", lazy="select"
    )
    decisions: Mapped[list["ReviewDecision"]] = relationship(
        "ReviewDecision", back_populates="finding", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Finding id={self.id} type={self.finding_type} severity={self.severity}>"


class FindingCitation(UUIDMixin, Base):
    __tablename__ = "finding_citations"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("item_versions.id", ondelete="CASCADE"), nullable=False
    )
    passage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("passages.id", ondelete="SET NULL"), nullable=True
    )
    exact_quote: Mapped[str] = mapped_column(Text, nullable=False)
    passage_text_at_citation: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="citations")
    item_version: Mapped["ItemVersion"] = relationship("ItemVersion")  # type: ignore[name-defined]
    passage: Mapped["Passage | None"] = relationship("Passage")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<FindingCitation id={self.id} finding_id={self.finding_id}>"


class EvidenceReceipt(UUIDMixin, Base):
    """Cryptographic and deterministic evidence receipt backing a finding."""
    __tablename__ = "evidence_receipts"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="evidence_receipts")

    def __repr__(self) -> str:
        return f"<EvidenceReceipt id={self.id} finding_id={self.finding_id}>"


FindingEvidence = EvidenceReceipt


class ReviewDecision(UUIDMixin, Base):
    """Reviewer decision on a validation finding or content item."""
    __tablename__ = "review_decisions"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decided_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(50), nullable=False)  # approved, overridden, dismissed
    reason_code: Mapped[OverrideReasonCode | None] = mapped_column(
        Enum(OverrideReasonCode, name="override_reason_code"), nullable=True
    )
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="decisions")
    reviewer: Mapped["User"] = relationship("User")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<ReviewDecision id={self.id} finding_id={self.finding_id} decision={self.decision}>"
