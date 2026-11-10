"""Add tenant embedding metadata and dimensioned Gemini vectors.

Revision ID: 003_ai_provider_metadata
Revises: 002_model_schema_alignment
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "003_ai_provider_metadata"
down_revision = "002_model_schema_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organisations",
        sa.Column("embedding_provider", sa.String(length=32), nullable=False, server_default="mock"),
    )
    op.add_column(
        "organisations",
        sa.Column("embedding_model", sa.String(length=100), nullable=True, server_default="hash-embedding-v1"),
    )
    op.alter_column("organisations", "embedding_model", server_default=None)
    op.add_column("passages", sa.Column("embedding", Vector(768), nullable=True))
    op.add_column(
        "validation_jobs",
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("validation_jobs", "fallback_used")
    op.drop_column("passages", "embedding")
    op.drop_column("organisations", "embedding_model")
    op.drop_column("organisations", "embedding_provider")
