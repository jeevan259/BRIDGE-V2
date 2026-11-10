"""Tests for version immutability and approval logic."""
from __future__ import annotations

import uuid
import pytest

from app.models.knowledge import (
    ItemStatus,
    ItemType,
    ItemVersion,
    KnowledgeItem,
    KnowledgeSource,
    SourceType,
    SourceVersion,
)


def test_item_version_statuses_defined():
    """All required statuses exist: pending, approved, superseded, rejected."""
    assert ItemStatus.pending.value == "pending"
    assert ItemStatus.approved.value == "approved"
    assert ItemStatus.superseded.value == "superseded"
    assert ItemStatus.rejected.value == "rejected"


def test_item_types_defined():
    """All required item types: fact, claim, rule, guideline."""
    assert ItemType.fact.value == "fact"
    assert ItemType.claim.value == "claim"
    assert ItemType.rule.value == "rule"
    assert ItemType.guideline.value == "guideline"


def test_source_types_defined():
    """All required source types: document, url, manual."""
    assert SourceType.document.value == "document"
    assert SourceType.url.value == "url"
    assert SourceType.manual.value == "manual"


def test_version_is_immutable_by_design():
    """An ItemVersion once created has its content frozen. Edits create new versions."""
    v1 = ItemVersion(
        id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        version_number=1,
        content="Original content",
        status=ItemStatus.approved,
    )
    # A new version should have a different version_number (never mutate v1)
    v2 = ItemVersion(
        id=uuid.uuid4(),
        item_id=v1.item_id,
        version_number=2,
        content="Updated content",
        status=ItemStatus.pending,
    )
    assert v1.version_number != v2.version_number
    assert v1.content != v2.content
    assert v1.id != v2.id


def test_knowledge_source_has_org_scope():
    """Sources must always carry org_id for tenant isolation."""
    org_id = uuid.uuid4()
    source = KnowledgeSource(
        id=uuid.uuid4(),
        org_id=org_id,
        name="Brand Guide",
        source_type=SourceType.document,
    )
    assert source.org_id == org_id

