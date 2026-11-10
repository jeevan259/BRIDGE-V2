"""Align initial Neon schema with current ORM models.

Revision ID: 002_model_schema_alignment
Revises: 001_initial
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002_model_schema_alignment"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_events",
        sa.Column("outcome", sa.String(length=32), nullable=False, server_default="success"),
    )
    op.add_column("audit_events", sa.Column("correlation_id", sa.String(length=64), nullable=True))

    op.add_column("knowledge_items", sa.Column("stable_identifier", sa.String(length=64), nullable=True))
    op.create_index("ix_knowledge_items_stable_identifier", "knowledge_items", ["stable_identifier"])

    op.add_column("item_versions", sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("item_versions", sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_item_versions_owner_id_users",
        "item_versions",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("item_versions", sa.Column("provenance", sa.Text(), nullable=True))
    op.add_column("item_versions", sa.Column("rule_config_json", postgresql.JSONB(), nullable=True))

    op.add_column("passages", sa.Column("embedding_json", postgresql.JSONB(), nullable=True))

    op.create_table(
        "content_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content_identifier", sa.String(length=500), nullable=False),
        sa.Column("channel", sa.String(length=100), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_content_items_org_id", "content_items", ["org_id"])
    op.create_index("ix_content_items_content_identifier", "content_items", ["content_identifier"])

    op.create_table(
        "content_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["content_items.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_content_snapshots_content_id", "content_snapshots", ["content_id"])

    op.create_table(
        "review_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("reason_code", postgresql.ENUM(
            "rule_unclear", "context_exception", "finding_incorrect",
            "source_not_relevant", "content_corrected", "other",
            name="override_reason_code", create_type=False,
        ), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_review_decisions_finding_id", "review_decisions", ["finding_id"])

    op.add_column("validation_jobs", sa.Column("rule_set_version", sa.String(length=50), nullable=True))
    op.add_column("validation_jobs", sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_validation_jobs_snapshot_id_content_snapshots",
        "validation_jobs", "content_snapshots", ["snapshot_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_validation_jobs_snapshot_id_content_snapshots", "validation_jobs", type_="foreignkey"
    )
    op.drop_column("validation_jobs", "snapshot_id")
    op.drop_column("validation_jobs", "rule_set_version")
    op.drop_index("ix_review_decisions_finding_id", table_name="review_decisions")
    op.drop_table("review_decisions")
    op.drop_index("ix_content_snapshots_content_id", table_name="content_snapshots")
    op.drop_table("content_snapshots")
    op.drop_index("ix_content_items_content_identifier", table_name="content_items")
    op.drop_index("ix_content_items_org_id", table_name="content_items")
    op.drop_table("content_items")

    op.drop_column("passages", "embedding_json")

    op.drop_column("item_versions", "rule_config_json")
    op.drop_column("item_versions", "provenance")
    op.drop_constraint("fk_item_versions_owner_id_users", "item_versions", type_="foreignkey")
    op.drop_column("item_versions", "owner_id")
    op.drop_column("item_versions", "effective_date")

    op.drop_index("ix_knowledge_items_stable_identifier", table_name="knowledge_items")
    op.drop_column("knowledge_items", "stable_identifier")

    op.drop_column("audit_events", "correlation_id")
    op.drop_column("audit_events", "outcome")
