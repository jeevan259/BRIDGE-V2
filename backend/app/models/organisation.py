"""Organisation model."""
from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Organisation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(32), default="mock", server_default="mock", nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="organisation", lazy="select")  # type: ignore[name-defined]
    knowledge_sources: Mapped[list["KnowledgeSource"]] = relationship(  # type: ignore[name-defined]
        "KnowledgeSource", back_populates="organisation", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Organisation id={self.id} slug={self.slug!r}>"
