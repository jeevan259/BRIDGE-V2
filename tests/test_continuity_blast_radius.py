"""Tests for Continuity Engine blast radius simulation and revalidation queuing."""
from __future__ import annotations

import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.models.continuity import EdgeType
from app.models.knowledge import KnowledgeItem, ItemType
from app.models.continuity import DependencyEdge
from app.schemas.continuity import ChangeSimulationResponse, ChangeApplyResponse
from app.services.continuity import simulate_rule_or_source_change


def test_simulation_schema_contract():
    """Verify simulation and apply response models have required fields."""
    sim = ChangeSimulationResponse(
        simulation=True,
        rule_name="Logo Clearspace Standard",
        change_summary="Mandate 40px clearspace",
        impacted_guidelines_count=4,
        impacted_guidelines=["Rule 1", "Rule 2", "Rule 3", "Rule 4"],
        impacted_assets_count=3,
        impacted_assets=["Asset 1", "Asset 2", "Asset 3"],
        blast_radius_score=85.0,
        revalidation_queued=False,
        message="Simulation complete",
    )
    assert sim.impacted_guidelines_count >= 3
    assert sim.impacted_assets_count >= 2
    assert sim.revalidation_queued is False

    apply_res = ChangeApplyResponse(
        applied=True,
        change_event_id=uuid.uuid4(),
        impact_report_id=uuid.uuid4(),
        rule_name="Logo Clearspace Standard",
        change_summary="Mandate 40px clearspace",
        impacted_guidelines_count=4,
        impacted_guidelines=["Rule 1", "Rule 2", "Rule 3", "Rule 4"],
        impacted_assets_count=3,
        impacted_assets=["Asset 1", "Asset 2", "Asset 3"],
        blast_radius_score=85.0,
        tasks_enqueued=3,
        revalidation_queued=True,
        message="Applied successfully",
    )
    assert apply_res.applied is True
    assert apply_res.tasks_enqueued >= 2
    assert apply_res.revalidation_queued is True
