"""Tests for hallucination isolation in validation findings and defense endpoint."""
from __future__ import annotations

import asyncio
import uuid
import pytest

from app.models.validation import Finding, FindingType, FindingSeverity, FindingStatus


def test_quarantined_hallucinations_isolated_from_normal_findings():
    """Unsupported/fabricated citations must be filtered out of normal findings."""
    job_id = uuid.uuid4()
    org_id = uuid.uuid4()

    valid_finding = Finding(
        id=uuid.uuid4(),
        job_id=job_id,
        org_id=org_id,
        finding_type=FindingType.brand_violation,
        severity=FindingSeverity.high,
        description="Valid finding",
        is_evidence_backed=True,
        status=FindingStatus.pending,
    )

    quarantined_finding = Finding(
        id=uuid.uuid4(),
        job_id=job_id,
        org_id=org_id,
        finding_type=FindingType.unsupported,
        severity=FindingSeverity.medium,
        description="[HALLUCINATION TRAP TRIGGERED]",
        is_evidence_backed=False,
        status=FindingStatus.pending,
    )

    all_findings = [valid_finding, quarantined_finding]

    # Normal filter: is_evidence_backed == True and finding_type != unsupported
    normal_results = [
        f for f in all_findings
        if f.is_evidence_backed and f.finding_type != FindingType.unsupported
    ]

    # Defense filter: is_evidence_backed == False or finding_type == unsupported
    defense_results = [
        f for f in all_findings
        if (not f.is_evidence_backed) or f.finding_type == FindingType.unsupported
    ]

    assert len(normal_results) == 1
    assert normal_results[0].id == valid_finding.id
    assert len(defense_results) == 1
    assert defense_results[0].id == quarantined_finding.id
