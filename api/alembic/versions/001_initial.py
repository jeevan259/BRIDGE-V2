"""Initial schema — all BRIDGE v2 tables.

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"vector\"")

    user_role = postgresql.ENUM(
        "administrator", "brand_manager", "reviewer", "creator", "auditor",
        name="user_role"
    )
    user_role.create(op.get_bind())

    source_type = postgresql.ENUM("document", "url", "manual", name="source_type")
    source_type.create(op.get_bind())

    ingestion_status = postgresql.ENUM(
        "pending", "processing", "completed", "failed", name="ingestion_status"
    )
    ingestion_status.create(op.get_bind())

    item_type = postgresql.ENUM("fact", "claim", "rule", "guideline", name="item_type")
    item_type.create(op.get_bind())

    item_status = postgresql.ENUM(
        "pending", "approved", "superseded", "rejected", name="item_status"
    )
    item_status.create(op.get_bind())

    job_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", name="job_status"
    )
    job_status.create(op.get_bind())

    finding_type = postgresql.ENUM(
        "brand_violation", "tone_issue", "factual_claim", "guideline_breach", "unsupported",
        name="finding_type"
    )
    finding_type.create(op.get_bind())

    finding_severity = postgresql.ENUM("high", "medium", "low", "info", name="finding_severity")
    finding_severity.create(op.get_bind())

    finding_status = postgresql.ENUM(
        "pending", "confirmed", "overridden", "dismissed", name="finding_status"
    )
    finding_status.create(op.get_bind())

    override_reason_code = postgresql.ENUM(
        "rule_unclear", "context_exception", "finding_incorrect",
        "source_not_relevant", "content_corrected", "other",
        name="override_reason_code"
    )
    override_reason_code.create(op.get_bind())

    edge_type = postgresql.ENUM("confirmed", "possible", name="edge_type")
    edge_type.create(op.get_bind())

    revalidation_priority = postgresql.ENUM("high", "medium", "low", name="revalidation_priority")
    revalidation_priority.create(op.get_bind())

    revalidation_status = postgresql.ENUM(
        "pending", "in_progress", "completed", "dismissed", name="revalidation_status"
    )
    revalidation_status.create(op.get_bind())

    signal_source_type = postgresql.ENUM(
        "override", "reviewer_comment", "external_feedback", name="signal_source_type"
    )
    signal_source_type.create(op.get_bind())

    signal_severity = postgresql.ENUM("high", "medium", "low", name="signal_severity")
    signal_severity.create(op.get_bind())

    recommendation_status = postgresql.ENUM(
        "pending", "approved", "rejected", name="recommendation_status"
    )
    recommendation_status.create(op.get_bind())

    job_queue_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", name="job_queue_status"
    )
    job_queue_status.create(op.get_bind())

    # ── organisations ─────────────────────────────────────────────────────────
    op.create_table(
        "organisations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_organisations_slug", "organisations", ["slug"], unique=True)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("role", sa.Enum("administrator", "brand_manager", "reviewer", "creator",
                                   "auditor", name="user_role", create_type=False), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    # ── knowledge_sources (create without FK to source_versions first) ────────
    op.create_table(
        "knowledge_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_type", sa.Enum("document", "url", "manual", name="source_type",
                                          create_type=False), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_knowledge_sources_org_id", "knowledge_sources", ["org_id"])

    # ── source_versions ───────────────────────────────────────────────────────
    op.create_table(
        "source_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("file_path", sa.Text, nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("content_text", sa.Text, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column("ingestion_status", sa.Enum(
            "pending", "processing", "completed", "failed",
            name="ingestion_status", create_type=False
        ), nullable=False, server_default="pending"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_source_versions_source_id", "source_versions", ["source_id"])
    # Partial unique index: at most one is_current=true per source
    op.create_index(
        "uix_source_versions_is_current",
        "source_versions",
        ["source_id"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )

    # Now add FK from knowledge_sources to source_versions
    op.create_foreign_key(
        "fk_knowledge_sources_current_version",
        "knowledge_sources", "source_versions",
        ["current_version_id"], ["id"],
        ondelete="SET NULL",
    )

    # ── passages ──────────────────────────────────────────────────────────────
    op.create_table(
        "passages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("passage_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("char_start", sa.Integer, nullable=False),
        sa.Column("char_end", sa.Integer, nullable=False),
    )
    op.create_index("ix_passages_version_id", "passages", ["version_id"])
    op.create_index("ix_passages_source_id", "passages", ["source_id"])
    op.create_index("ix_passages_org_id", "passages", ["org_id"])

    # ── knowledge_items ───────────────────────────────────────────────────────
    op.create_table(
        "knowledge_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.Enum("fact", "claim", "rule", "guideline",
                                        name="item_type", create_type=False), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_knowledge_items_org_id", "knowledge_items", ["org_id"])
    op.create_index("ix_knowledge_items_source_id", "knowledge_items", ["source_id"])

    # ── item_versions ─────────────────────────────────────────────────────────
    op.create_table(
        "item_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("source_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", sa.Enum("pending", "approved", "superseded", "rejected",
                                     name="item_status", create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text, nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_item_versions_item_id", "item_versions", ["item_id"])
    # Partial unique: at most one approved version per item
    op.create_index(
        "uix_item_versions_approved",
        "item_versions",
        ["item_id"],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
    )

    # Now add FK from knowledge_items to item_versions
    op.create_foreign_key(
        "fk_knowledge_items_current_version",
        "knowledge_items", "item_versions",
        ["current_version_id"], ["id"],
        ondelete="SET NULL",
    )

    # ── validation_jobs ───────────────────────────────────────────────────────
    op.create_table(
        "validation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_text", sa.Text, nullable=False),
        sa.Column("content_title", sa.String(500), nullable=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Enum("pending", "running", "completed", "failed",
                                     name="job_status", create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("ai_provider_used", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index("ix_validation_jobs_org_id", "validation_jobs", ["org_id"])

    # ── findings ──────────────────────────────────────────────────────────────
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("validation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_type", sa.Enum(
            "brand_violation", "tone_issue", "factual_claim", "guideline_breach", "unsupported",
            name="finding_type", create_type=False
        ), nullable=False),
        sa.Column("severity", sa.Enum("high", "medium", "low", "info",
                                       name="finding_severity", create_type=False), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("is_evidence_backed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.Enum("pending", "confirmed", "overridden", "dismissed",
                                     name="finding_status", create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("override_reason_code", sa.Enum(
            "rule_unclear", "context_exception", "finding_incorrect",
            "source_not_relevant", "content_corrected", "other",
            name="override_reason_code", create_type=False
        ), nullable=True),
        sa.Column("override_reason_text", sa.Text, nullable=True),
        sa.Column("overridden_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("overridden_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_findings_job_id", "findings", ["job_id"])
    op.create_index("ix_findings_org_id", "findings", ["org_id"])

    # ── finding_citations ─────────────────────────────────────────────────────
    op.create_table(
        "finding_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("item_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("passage_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("passages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("exact_quote", sa.Text, nullable=False),
        sa.Column("passage_text_at_citation", sa.Text, nullable=False),
    )
    op.create_index("ix_finding_citations_finding_id", "finding_citations", ["finding_id"])

    # ── evidence_receipts ─────────────────────────────────────────────────────
    op.create_table(
        "evidence_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receipt_json", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_evidence_receipts_finding_id", "evidence_receipts", ["finding_id"])

    # ── dependency_edges ──────────────────────────────────────────────────────
    op.create_table(
        "dependency_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_identifier", sa.Text, nullable=False),
        sa.Column("content_title", sa.String(500), nullable=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("edge_type", sa.Enum("confirmed", "possible",
                                        name="edge_type", create_type=False),
                  nullable=False, server_default="possible"),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("content_identifier", "item_id", name="uq_dep_edge_content_item"),
    )
    op.create_index("ix_dependency_edges_org_id", "dependency_edges", ["org_id"])
    op.create_index("ix_dependency_edges_item_id", "dependency_edges", ["item_id"])

    # ── change_events ─────────────────────────────────────────────────────────
    op.create_table(
        "change_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("source_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("new_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("source_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("change_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_change_events_org_id", "change_events", ["org_id"])
    op.create_index("ix_change_events_source_id", "change_events", ["source_id"])

    # ── impact_reports ────────────────────────────────────────────────────────
    op.create_table(
        "impact_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("change_event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("change_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("affected_content_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("blast_radius_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report_json", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_impact_reports_change_event_id", "impact_reports", ["change_event_id"])
    op.create_index("ix_impact_reports_org_id", "impact_reports", ["org_id"])

    # ── revalidation_tasks ────────────────────────────────────────────────────
    op.create_table(
        "revalidation_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("impact_report_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("impact_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_identifier", sa.Text, nullable=False),
        sa.Column("content_title", sa.String(500), nullable=True),
        sa.Column("priority", sa.Enum("high", "medium", "low",
                                       name="revalidation_priority", create_type=False), nullable=False),
        sa.Column("exposure_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("status", sa.Enum("pending", "in_progress", "completed", "dismissed",
                                     name="revalidation_status", create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_revalidation_tasks_impact_report_id", "revalidation_tasks", ["impact_report_id"])
    op.create_index("ix_revalidation_tasks_org_id", "revalidation_tasks", ["org_id"])

    # ── review_signals ────────────────────────────────────────────────────────
    op.create_table(
        "review_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.Enum("override", "reviewer_comment", "external_feedback",
                                          name="signal_source_type", create_type=False), nullable=False),
        sa.Column("signal_text", sa.Text, nullable=False),
        sa.Column("severity", sa.Enum("high", "medium", "low",
                                       name="signal_severity", create_type=False), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_review_signals_org_id", "review_signals", ["org_id"])
    op.create_index("ix_review_signals_item_id", "review_signals", ["item_id"])

    # ── ambiguity_analyses ────────────────────────────────────────────────────
    op.create_table(
        "ambiguity_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_signal_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("analysis_summary", sa.Text, nullable=False),
        sa.Column("ambiguous_aspects_json", postgresql.JSONB, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ai_provider_used", sa.String(50), nullable=True),
    )
    op.create_index("ix_ambiguity_analyses_org_id", "ambiguity_analyses", ["org_id"])
    op.create_index("ix_ambiguity_analyses_item_id", "ambiguity_analyses", ["item_id"])

    # ── guideline_recommendations ─────────────────────────────────────────────
    op.create_table(
        "guideline_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ambiguity_analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("proposed_content", sa.Text, nullable=False),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("pending", "approved", "rejected",
                                     name="recommendation_status", create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_guideline_recommendations_org_id", "guideline_recommendations", ["org_id"])
    op.create_index("ix_guideline_recommendations_analysis_id", "guideline_recommendations", ["analysis_id"])

    # ── audit_events ──────────────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_email", sa.Text, nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("diff_json", postgresql.JSONB, nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=True),
        sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_org_id", "audit_events", ["org_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # ── jobs (background queue) ───────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column("payload_json", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.Enum("pending", "running", "completed", "failed",
                                     name="job_queue_status", create_type=False),
                  nullable=False, server_default="pending"),
        sa.Column("result_json", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_org_id", "jobs", ["org_id"])
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    # ── Invariant: Single current approved version per record ────────────────
    op.create_index(
        "uq_one_approved_version_per_record",
        "item_versions",
        ["item_id"],
        unique=True,
        postgresql_where=sa.text("status = 'approved'"),
    )

    # ── Invariant: Append-only immutable audit ledger trigger ─────────────────
    op.execute("""
    CREATE OR REPLACE FUNCTION block_audit_mutation() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'UPDATE or DELETE is prohibited on immutable audit_events ledger.';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS trg_block_audit_mutation ON audit_events;
    CREATE TRIGGER trg_block_audit_mutation
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION block_audit_mutation();
    """)


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("audit_events")
    op.drop_table("guideline_recommendations")
    op.drop_table("ambiguity_analyses")
    op.drop_table("review_signals")
    op.drop_table("revalidation_tasks")
    op.drop_table("impact_reports")
    op.drop_table("change_events")
    op.drop_table("dependency_edges")
    op.drop_table("evidence_receipts")
    op.drop_table("finding_citations")
    op.drop_table("findings")
    op.drop_table("validation_jobs")

    op.drop_constraint("fk_knowledge_items_current_version", "knowledge_items", type_="foreignkey")
    op.drop_table("item_versions")
    op.drop_table("knowledge_items")
    op.drop_table("passages")

    op.drop_constraint("fk_knowledge_sources_current_version", "knowledge_sources", type_="foreignkey")
    op.drop_table("source_versions")
    op.drop_table("knowledge_sources")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("organisations")

    # Drop enums
    for enum_name in [
        "job_queue_status", "recommendation_status", "signal_severity",
        "signal_source_type", "revalidation_status", "revalidation_priority",
        "edge_type", "override_reason_code", "finding_status", "finding_severity",
        "finding_type", "job_status", "item_status", "item_type",
        "ingestion_status", "source_type", "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
