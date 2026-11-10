"""Knowledge domain models — KnowledgeSource, KnowledgeItem, ItemVersion, Passage."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TimestampMixin, UUIDMixin


class SourceType(str, enum.Enum):
    document = "document"
    url = "url"
    manual = "manual"


class IngestionStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ItemType(str, enum.Enum):
    fact = "fact"
    claim = "claim"
    rule = "rule"
    guideline = "guideline"
    asset = "asset"


class ItemStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    pending_verification = "pending_verification"
    approved = "approved"
    superseded = "superseded"
    rejected = "rejected"


class KnowledgeSource(UUIDMixin, TimestampMixin, Base):
    """Authoritative document, URL, or manual source defining brand standards."""
    __tablename__ = "knowledge_sources"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="SET NULL", use_alter=True), nullable=True
    )

    # Relationships
    organisation: Mapped["Organisation"] = relationship(  # type: ignore[name-defined]
        "Organisation", back_populates="knowledge_sources"
    )
    versions: Mapped[list["SourceVersion"]] = relationship(
        "SourceVersion", back_populates="source",
        foreign_keys="[SourceVersion.source_id]", lazy="select"
    )
    current_version: Mapped["SourceVersion | None"] = relationship(
        "SourceVersion", foreign_keys=[current_version_id], lazy="select"
    )
    passages: Mapped[list["Passage"]] = relationship(
        "Passage", back_populates="source", lazy="select"
    )
    items: Mapped[list["KnowledgeItem"]] = relationship(
        "KnowledgeItem", back_populates="source", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<KnowledgeSource id={self.id} name={self.name!r}>"


BrandDocument = KnowledgeSource


class SourceVersion(UUIDMixin, TimestampMixin, Base):
    """Versioned snapshot of an ingested KnowledgeSource."""
    __tablename__ = "source_versions"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ingestion_status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus, name="ingestion_status"), nullable=False, default=IngestionStatus.pending
    )
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    source: Mapped["KnowledgeSource"] = relationship(
        "KnowledgeSource", back_populates="versions", foreign_keys=[source_id]
    )
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])  # type: ignore[name-defined]
    passages: Mapped[list["Passage"]] = relationship(
        "Passage", back_populates="version", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<SourceVersion id={self.id} source_id={self.source_id} v={self.version_number}>"


class Passage(UUIDMixin, Base):
    """Authoritative passage chunk with exact offsets and optional vector embedding."""
    __tablename__ = "passages"

    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    passage_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    embedding_vector: Mapped[list[float] | None] = mapped_column("embedding", Vector(768), nullable=True)

    # Relationships
    version: Mapped["SourceVersion"] = relationship("SourceVersion", back_populates="passages")
    source: Mapped["KnowledgeSource"] = relationship("KnowledgeSource", back_populates="passages")

    def __repr__(self) -> str:
        return f"<Passage id={self.id} source_id={self.source_id} idx={self.passage_index}>"


KnowledgePassage = Passage


class KnowledgeItem(UUIDMixin, TimestampMixin, Base):
    """Governed knowledge record (fact, claim, rule, guideline) with stable identifier."""
    __tablename__ = "knowledge_items"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stable_identifier: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )  # e.g. F-014, R-001
    item_type: Mapped[ItemType] = mapped_column(
        Enum(ItemType, name="item_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("item_versions.id", ondelete="SET NULL", use_alter=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    source: Mapped["KnowledgeSource"] = relationship("KnowledgeSource", back_populates="items")
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])  # type: ignore[name-defined]
    versions: Mapped[list["ItemVersion"]] = relationship(
        "ItemVersion", back_populates="item",
        foreign_keys="[ItemVersion.item_id]", lazy="select"
    )
    current_version: Mapped["ItemVersion | None"] = relationship(
        "ItemVersion", foreign_keys=[current_version_id], lazy="select"
    )

    @property
    def kind(self) -> ItemType:
        return self.item_type

    def __repr__(self) -> str:
        return f"<KnowledgeItem id={self.id} stable_id={self.stable_identifier} title={self.title!r}>"


KnowledgeRecord = KnowledgeItem


class ItemVersion(UUIDMixin, TimestampMixin, Base):
    """
    Immutable version of a KnowledgeItem.
    Enforces invariant: AT MOST ONE current approved version per record via partial unique index.
    """
    __tablename__ = "item_versions"
    __table_args__ = (
        Index(
            "uq_one_approved_version_per_record",
            "item_id",
            unique=True,
            postgresql_where=(mapped_column("status") == "approved"),
        ),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_versions.id", ondelete="SET NULL"), nullable=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ItemStatus] = mapped_column(
        Enum(ItemStatus, name="item_status"), nullable=False, default=ItemStatus.draft
    )
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    provenance: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_config_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    item: Mapped["KnowledgeItem"] = relationship(
        "KnowledgeItem", back_populates="versions", foreign_keys=[item_id]
    )
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by])  # type: ignore[name-defined]
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])  # type: ignore[name-defined]

    @property
    def value(self) -> str:
        return self.content

    @property
    def approved_by(self) -> uuid.UUID | None:
        return self.reviewed_by

    def __repr__(self) -> str:
        return f"<ItemVersion id={self.id} item_id={self.item_id} v={self.version_number} status={self.status}>"


KnowledgeVersion = ItemVersion
