"""Record when validation used deterministic AI-limited mode.

Revision ID: 004_ai_limited_mode
Revises: 003_ai_provider_metadata
"""
from alembic import op
import sqlalchemy as sa


revision = "004_ai_limited_mode"
down_revision = "003_ai_provider_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "validation_jobs",
        sa.Column("ai_limited_mode", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("validation_jobs", "ai_limited_mode")
