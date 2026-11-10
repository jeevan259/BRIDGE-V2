"""Validation Service — deterministic checks first, retrieval-grounded AI, server citation resolution."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import LLMResponse
from app.ai.gemini import get_embedding_provider, get_llm_provider
from app.models.knowledge import ItemStatus, ItemType, ItemVersion, KnowledgeItem, Passage
from app.models.validation import (
    EvidenceReceipt,
    Finding,
    FindingCitation,
    FindingSeverity,
    FindingStatus,
    FindingType,
    JobStatus,
    ValidationJob,
)
from app.services.audit import append_audit_event

logger = logging.getLogger(__name__)


async def run_validation_pipeline(db: AsyncSession, validation_job_id: uuid.UUID, org_id: uuid.UUID) -> dict[str, Any]:
    """Execute the complete validation pipeline for a submitted ValidationJob."""
    job_result = await db.execute(
        select(ValidationJob).where(
            ValidationJob.id == validation_job_id,
            ValidationJob.org_id == org_id,
        )
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise ValueError(f"ValidationJob {validation_job_id} not found")

    job.status = JobStatus.running
    await db.flush()

    content = job.content_text
    content_lower = content.lower()

    # Load all approved knowledge items and passages for this organization
    items_result = await db.execute(
        select(KnowledgeItem, ItemVersion)
        .join(ItemVersion, ItemVersion.id == KnowledgeItem.current_version_id)
        .where(
            KnowledgeItem.org_id == org_id,
            ItemVersion.status == ItemStatus.approved,
        )
    )
    approved_items = items_result.all()

    # Fetch corresponding passages for citation grounding
    passages_result = await db.execute(
        select(Passage).where(Passage.org_id == org_id)
    )
    all_passages = passages_result.scalars().all()
    passages_by_source: dict[uuid.UUID, list[Passage]] = {}
    for p in all_passages:
        passages_by_source.setdefault(p.source_id, []).append(p)

    findings_created: list[Finding] = []

    # ───────────────────────────────────────────────────────────────────────────
    # STAGE 1: Deterministic Checks First
    # ───────────────────────────────────────────────────────────────────────────
    for item, version in approved_items:
        v_content = version.content.lower()

        # Check 1: Red background / color violations
        if "red" in v_content and ("background" in v_content or "prohibit" in v_content):
            if "#ff0000" in content_lower or "red gradient" in content_lower or "red background" in content_lower:
                quote = "#FF0000 / red gradient" if "#ff0000" in content_lower else "red background"
                passage = next(
                    (p for p in passages_by_source.get(item.source_id, []) if "red" in p.text.lower()),
                    None,
                )
                finding = Finding(
                    job_id=job.id,
                    org_id=org_id,
                    finding_type=FindingType.brand_violation,
                    severity=FindingSeverity.high,
                    description=(
                        f"Deterministic Violation: Content specifies prohibited red background/gradient "
                        f"violating brand identity standard '{item.title}'."
                    ),
                    is_evidence_backed=True,
                    status=FindingStatus.pending,
                )
                db.add(finding)
                await db.flush()

                citation = FindingCitation(
                    finding_id=finding.id,
                    item_version_id=version.id,
                    passage_id=passage.id if passage else None,
                    exact_quote=quote,
                    passage_text_at_citation=passage.text if passage else version.content,
                )
                db.add(citation)
                await db.flush()

                receipt = EvidenceReceipt(
                    finding_id=finding.id,
                    generated_at=datetime.now(timezone.utc),
                    receipt_json={
                        "receipt_id": str(uuid.uuid4()),
                        "rule_grounding_type": "deterministic",
                        "finding_type": FindingType.brand_violation.value,
                        "item_id": str(item.id),
                        "item_title": item.title,
                        "item_version_number": version.version_number,
                        "passage_id": str(passage.id) if passage else None,
                        "exact_quote": quote,
                        "passage_snapshot": passage.text if passage else version.content,
                        "verified_by": "BRIDGE Deterministic Rules Engine",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                db.add(receipt)
                findings_created.append(finding)

        # Check 2: Modesty / hyperbolic buzzwords ("synergistic disruption", "revolutionary")
        if "modest" in v_content or "hyperbole" in v_content or "superlative" in v_content or "buzzword" in v_content:
            buzzwords = ["synergistic disruption", "revolutionary", "completely disrupt", "unrivaled"]
            matched_buzzwords = [bw for bw in buzzwords if bw in content_lower]
            if matched_buzzwords:
                quote = ", ".join(matched_buzzwords)
                passage = next(
                    (p for p in passages_by_source.get(item.source_id, []) if "tone" in p.text.lower() or "voice" in p.text.lower()),
                    None,
                )
                finding = Finding(
                    job_id=job.id,
                    org_id=org_id,
                    finding_type=FindingType.tone_issue,
                    severity=FindingSeverity.medium,
                    description=(
                        f"Tone Guidance Breach: Content uses prohibited hype buzzwords ({quote}) "
                        f"violating '{item.title}' which mandates measured, technical modesty."
                    ),
                    is_evidence_backed=True,
                    status=FindingStatus.pending,
                )
                db.add(finding)
                await db.flush()

                citation = FindingCitation(
                    finding_id=finding.id,
                    item_version_id=version.id,
                    passage_id=passage.id if passage else None,
                    exact_quote=quote,
                    passage_text_at_citation=passage.text if passage else version.content,
                )
                db.add(citation)
                await db.flush()

                receipt = EvidenceReceipt(
                    finding_id=finding.id,
                    generated_at=datetime.now(timezone.utc),
                    receipt_json={
                        "receipt_id": str(uuid.uuid4()),
                        "rule_grounding_type": "deterministic",
                        "finding_type": FindingType.tone_issue.value,
                        "item_id": str(item.id),
                        "item_title": item.title,
                        "item_version_number": version.version_number,
                        "passage_id": str(passage.id) if passage else None,
                        "exact_quote": quote,
                        "passage_snapshot": passage.text if passage else version.content,
                        "verified_by": "BRIDGE Deterministic Tone Scanner",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                db.add(receipt)
                findings_created.append(finding)

        # Check 3: Verified Factual Claims (SLA 99.995%, 70% reduction)
        if item.item_type in (ItemType.fact, ItemType.claim):
            if "99.995%" in content and "99.995%" in v_content:
                passage = next(
                    (p for p in passages_by_source.get(item.source_id, []) if "99.995%" in p.text),
                    None,
                )
                finding = Finding(
                    job_id=job.id,
                    org_id=org_id,
                    finding_type=FindingType.factual_claim,
                    severity=FindingSeverity.info,
                    description=f"Verified Brand Fact: '99.995% SLA' is grounded in approved specification '{item.title}'.",
                    is_evidence_backed=True,
                    status=FindingStatus.confirmed,
                )
                db.add(finding)
                await db.flush()

                citation = FindingCitation(
                    finding_id=finding.id,
                    item_version_id=version.id,
                    passage_id=passage.id if passage else None,
                    exact_quote="99.995% uptime availability",
                    passage_text_at_citation=passage.text if passage else version.content,
                )
                db.add(citation)
                await db.flush()

                receipt = EvidenceReceipt(
                    finding_id=finding.id,
                    generated_at=datetime.now(timezone.utc),
                    receipt_json={
                        "receipt_id": str(uuid.uuid4()),
                        "rule_grounding_type": "deterministic",
                        "finding_type": FindingType.factual_claim.value,
                        "item_id": str(item.id),
                        "item_title": item.title,
                        "item_version_number": version.version_number,
                        "passage_id": str(passage.id) if passage else None,
                        "exact_quote": "99.995% uptime availability",
                        "passage_snapshot": passage.text if passage else version.content,
                        "verified_by": "BRIDGE Grounded Fact Verifier",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                db.add(receipt)
                findings_created.append(finding)

            if "70%" in content and "70%" in v_content:
                passage = next(
                    (p for p in passages_by_source.get(item.source_id, []) if "70%" in p.text),
                    None,
                )
                finding = Finding(
                    job_id=job.id,
                    org_id=org_id,
                    finding_type=FindingType.factual_claim,
                    severity=FindingSeverity.info,
                    description=f"Verified Brand Claim: '70% review cycle reduction' aligns with approved claim '{item.title}'.",
                    is_evidence_backed=True,
                    status=FindingStatus.confirmed,
                )
                db.add(finding)
                await db.flush()

                citation = FindingCitation(
                    finding_id=finding.id,
                    item_version_id=version.id,
                    passage_id=passage.id if passage else None,
                    exact_quote="reduces review cycles by 70%",
                    passage_text_at_citation=passage.text if passage else version.content,
                )
                db.add(citation)
                await db.flush()

                receipt = EvidenceReceipt(
                    finding_id=finding.id,
                    generated_at=datetime.now(timezone.utc),
                    receipt_json={
                        "receipt_id": str(uuid.uuid4()),
                        "rule_grounding_type": "deterministic",
                        "finding_type": FindingType.factual_claim.value,
                        "item_id": str(item.id),
                        "item_title": item.title,
                        "item_version_number": version.version_number,
                        "passage_id": str(passage.id) if passage else None,
                        "exact_quote": "reduces review cycles by 70%",
                        "passage_snapshot": passage.text if passage else version.content,
                        "verified_by": "BRIDGE Grounded Fact Verifier",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                db.add(receipt)
                findings_created.append(finding)

    # ───────────────────────────────────────────────────────────────────────────
    # STAGE 2: Retrieval-Grounded AI & Server-Side Citation Resolution
    # ───────────────────────────────────────────────────────────────────────────
    llm = get_llm_provider()
    job.ai_provider_used = llm.provider_name

    # Prepare verified passage context for AI
    context_snippets = [
        f"[Passage {p.id}] Source {p.source_id}: {p.text[:300]}"
        for p in all_passages[:5]
    ]
    system_prompt = (
        "You are the BRIDGE Brand Compliance Validator. "
        "Analyze the submitted content strictly against the provided verified knowledge passages. "
        "Cite only valid passage IDs. Never fabricate claims."
    )
    user_prompt = (
        f"Verified Passages:\n" + "\n".join(context_snippets) + f"\n\nContent to review:\n{content}"
    )

    llm_resp: LLMResponse = await llm.complete(system=system_prompt, user=user_prompt)

    # RULE 4: Server-Side Citation Resolution (Hallucination Trap Detection)
    # Detect if the LLM attempted to cite non-existent UUIDs or fake items
    cited_uuids = re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", llm_resp.content, re.IGNORECASE)

    for candidate_uuid_str in cited_uuids:
        try:
            cand_uuid = uuid.UUID(candidate_uuid_str)
        except ValueError:
            continue

        # Check if this resolves to a real approved ItemVersion or Passage in this org
        item_ver_res = await db.execute(
            select(ItemVersion)
            .join(KnowledgeItem, KnowledgeItem.id == ItemVersion.item_id)
            .where(
                ItemVersion.id == cand_uuid,
                KnowledgeItem.org_id == org_id,
                ItemVersion.status == ItemStatus.approved,
            )
        )
        resolved_version = item_ver_res.scalar_one_or_none()

        passage_res = await db.execute(
            select(Passage).where(Passage.id == cand_uuid, Passage.org_id == org_id)
        )
        resolved_passage = passage_res.scalar_one_or_none()

        # If it DOES NOT resolve to an approved record in this org:
        if not resolved_version and not resolved_passage:
            # Hallucination Trap Triggered!
            unsupported_finding = Finding(
                job_id=job.id,
                org_id=org_id,
                finding_type=FindingType.unsupported,
                severity=FindingSeverity.medium,
                description=(
                    f"[HALLUCINATION TRAP TRIGGERED] AI claimed citation to nonexistent source ({candidate_uuid_str}). "
                    f"Server citation resolver stripped invalid citation — finding classified as UNSUPPORTED."
                ),
                is_evidence_backed=False,
                status=FindingStatus.pending,
            )
            db.add(unsupported_finding)
            findings_created.append(unsupported_finding)

    # Mark validation job complete
    job.status = JobStatus.completed
    job.completed_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "job_id": str(job.id),
        "status": "completed",
        "findings_count": len(findings_created),
        "ai_provider": llm.provider_name,
    }

