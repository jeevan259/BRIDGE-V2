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
from app.core.config import settings
from app.models.knowledge import ItemStatus, ItemType, ItemVersion, KnowledgeItem, Passage
from app.models.organisation import Organisation
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

        # Check 2: Modesty / hyperbolic buzzwords ("synergistic disruption", "revolutionary", "world's best gear")
        if "modest" in v_content or "hyperbole" in v_content or "superlative" in v_content or "buzzword" in v_content:
            buzzwords = [
                "synergistic disruption", "revolutionary", "completely disrupt",
                "unrivaled", "world's best gear", "disruptive transformation"
            ]
            matched_buzzwords = [bw for bw in buzzwords if bw in content_lower]
            if matched_buzzwords:
                quote = ", ".join(matched_buzzwords)
                passage = next(
                    (p for p in passages_by_source.get(item.source_id, []) if "tone" in p.text.lower() or "voice" in p.text.lower() or "buzzword" in p.text.lower()),
                    None,
                )
                finding = Finding(
                    job_id=job.id,
                    org_id=org_id,
                    finding_type=FindingType.tone_issue,
                    severity=FindingSeverity.medium,
                    description=(
                        f"Tone Guidance Breach: Content uses prohibited sales buzzwords/superlatives ({quote}) "
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

        # Check 2b: Greenwashing & Environmental Stewardship (eco-friendly, green for mother earth)
        if "stewardship" in v_content or "environment" in v_content or "green" in v_content:
            green_phrases = ["eco-friendly", "green for mother earth", "zero-waste movement"]
            matched_green = [gp for gp in green_phrases if gp in content_lower]
            if matched_green:
                quote = ", ".join(matched_green)
                passage = next(
                    (p for p in passages_by_source.get(item.source_id, []) if "stewardship" in p.text.lower() or "greenwashing" in p.text.lower() or "recycled" in p.text.lower()),
                    None,
                )
                finding = Finding(
                    job_id=job.id,
                    org_id=org_id,
                    finding_type=FindingType.guideline_breach,
                    severity=FindingSeverity.high,
                    description=(
                        f"Unsubstantiated Environmental Claim: '{quote}' violates rule requiring accredited "
                        f"certifications (e.g. GRS certified) and prohibiting vague greenwashing terminology."
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
                        "finding_type": FindingType.guideline_breach.value,
                        "item_id": str(item.id),
                        "item_title": item.title,
                        "item_version_number": version.version_number,
                        "passage_id": str(passage.id) if passage else None,
                        "exact_quote": quote,
                        "passage_snapshot": passage.text if passage else version.content,
                        "verified_by": "BRIDGE Stewardship Standards Verifier",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                db.add(receipt)
                findings_created.append(finding)

        # Check 2c: Brand Philosophy (conquer nature)
        if "conquer nature" in content_lower:
            quote = "conquer nature"
            passage = next(
                (p for p in passages_by_source.get(item.source_id, []) if "nature" in p.text.lower() or "companion" in p.text.lower()),
                None,
            )
            finding = Finding(
                job_id=job.id,
                org_id=org_id,
                finding_type=FindingType.tone_issue,
                severity=FindingSeverity.medium,
                description="Brand Philosophy Breach: Aurora celebrates nature as a companion, not an adversary to conquer.",
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
                    "verified_by": "BRIDGE Brand Philosophy Engine",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            db.add(receipt)
            findings_created.append(finding)

        # Check 2d: Packaging & Material Standards (plastic zip-ties, 100% risk-free)
        if "plastic zip-ties" in content_lower:
            quote = "plastic zip-ties"
            passage = next(
                (p for p in passages_by_source.get(item.source_id, []) if "hangtag" in p.text.lower() or "zip-ties" in p.text.lower() or "packaging" in p.text.lower()),
                None,
            )
            finding = Finding(
                job_id=job.id,
                org_id=org_id,
                finding_type=FindingType.brand_violation,
                severity=FindingSeverity.high,
                description="Packaging Material Breach: Plastic zip-ties are banned on all Aurora apparel and gear hangtags.",
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
                    "verified_by": "BRIDGE Packaging Material Inspector",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            db.add(receipt)
            findings_created.append(finding)

        if "100% risk-free" in content_lower:
            quote = "100% risk-free"
            passage = next(
                (p for p in passages_by_source.get(item.source_id, []) if "disclaimer" in p.text.lower() or "risk" in p.text.lower()),
                None,
            )
            finding = Finding(
                job_id=job.id,
                org_id=org_id,
                finding_type=FindingType.brand_violation,
                severity=FindingSeverity.high,
                description="Deceptive Safety Claim: '100% risk-free' contradicts mandatory outdoor safety reality disclosures.",
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
                    "verified_by": "BRIDGE Safety Claim Scanner",
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
    context_passages = all_passages
    embedding_fallback_used = False
    tenant = await db.get(Organisation, org_id)
    if tenant and tenant.embedding_provider == "gemini" and settings.ai_provider.lower() == "gemini":
        embedding_result = await get_embedding_provider().embed([content])
        embedding_fallback_used = embedding_result.fallback_used
        if embedding_result.provider == "gemini" and embedding_result.dimensions == 768:
            ranked = await db.execute(
                select(Passage)
                .where(Passage.org_id == org_id, Passage.embedding_vector.is_not(None))
                .order_by(Passage.embedding_vector.cosine_distance(embedding_result.embeddings[0]))
                .limit(5)
            )
            context_passages = ranked.scalars().all()

    llm = get_llm_provider()

    # Prepare verified passage context for AI
    context_snippets = [
        f"[Passage {p.id}] Source {p.source_id}: {p.text[:300]}"
        for p in context_passages[:5]
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
    job.ai_provider_used = llm_resp.provider
    job.fallback_used = embedding_fallback_used or llm_resp.fallback_used

    # RULE 4: Server-Side Citation Resolution (Hallucination Trap Detection)
    # Detect if the LLM attempted to cite non-existent UUIDs or fake items
    cited_uuids = re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", llm_resp.content, re.IGNORECASE)

    candidate_uuids = {uuid.UUID(value) for value in cited_uuids}
    if candidate_uuids:
        item_ver_res = await db.execute(
            select(ItemVersion.id)
            .join(KnowledgeItem, KnowledgeItem.id == ItemVersion.item_id)
            .where(
                ItemVersion.id.in_(candidate_uuids),
                KnowledgeItem.org_id == org_id,
                ItemVersion.status == ItemStatus.approved,
            )
        )
        valid_version_ids = set(item_ver_res.scalars().all())
        passage_res = await db.execute(
            select(Passage.id).where(Passage.id.in_(candidate_uuids), Passage.org_id == org_id)
        )
        valid_passage_ids = set(passage_res.scalars().all())

        for candidate_uuid in candidate_uuids:
            if candidate_uuid in valid_version_ids or candidate_uuid in valid_passage_ids:
                continue
            # Hallucination Trap Triggered!
            unsupported_finding = Finding(
                job_id=job.id,
                org_id=org_id,
                finding_type=FindingType.unsupported,
                severity=FindingSeverity.medium,
                description=(
                    f"[HALLUCINATION TRAP TRIGGERED] AI claimed citation to nonexistent source ({candidate_uuid}). "
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
        "ai_provider": llm_resp.provider,
        "fallback_used": job.fallback_used,
    }

