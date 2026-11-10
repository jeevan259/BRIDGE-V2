"""Tests validating database schema invariants and model definitions."""
from __future__ import annotations

from app.models.audit import AuditEvent
from app.models.continuity import DependencyEdge, ImpactReport, RevalidationTask
from app.models.guideline import GuidelineRecommendation, ReviewSignal
from app.models.knowledge import BrandDocument, KnowledgePassage, KnowledgeRecord, KnowledgeVersion
from app.models.organisation import Organisation
from app.models.user import RefreshToken, User
from app.models.validation import ContentItem, ContentSnapshot, Finding, ValidationJob


def test_core_models_registered_and_configured():
    """Verify all primary P0 models are properly configured with table names."""
    assert Organisation.__tablename__ == "organisations"
    assert User.__tablename__ == "users"
    assert RefreshToken.__tablename__ == "refresh_tokens"
    assert BrandDocument.__tablename__ == "knowledge_sources"
    assert KnowledgeRecord.__tablename__ == "knowledge_items"
    assert KnowledgeVersion.__tablename__ == "item_versions"
    assert KnowledgePassage.__tablename__ == "passages"
    assert ContentItem.__tablename__ == "content_items"
    assert ContentSnapshot.__tablename__ == "content_snapshots"
    assert ValidationJob.__tablename__ == "validation_jobs"
    assert Finding.__tablename__ == "findings"
    assert DependencyEdge.__tablename__ == "dependency_edges"
    assert AuditEvent.__tablename__ == "audit_events"


def test_knowledge_version_partial_unique_index_defined():
    """Verify that KnowledgeVersion includes the partial unique index enforcing 1 approved version."""
    table_args = KnowledgeVersion.__table_args__
    assert table_args is not None
    index_names = [arg.name for arg in table_args if hasattr(arg, "name")]
    assert "uq_one_approved_version_per_record" in index_names

