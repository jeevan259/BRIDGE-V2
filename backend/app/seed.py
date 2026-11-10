"""Database seed script for BRIDGE v2 demo organization."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.audit import AuditEvent
from app.models.continuity import (
    ChangeEvent, DependencyEdge, EdgeType, ImpactReport,
    RevalidationPriority, RevalidationStatus, RevalidationTask,
)
from app.models.guideline import (
    AmbiguityAnalysis, GuidelineRecommendation, RecommendationStatus,
    ReviewSignal, SignalSeverity, SignalSourceType,
)
from app.models.knowledge import (
    IngestionStatus, ItemStatus, ItemType, ItemVersion,
    KnowledgeItem, KnowledgeSource, Passage, SourceType, SourceVersion,
)
from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.models.validation import (
    EvidenceReceipt, Finding, FindingCitation, FindingSeverity,
    FindingStatus, FindingType, JobStatus, OverrideReasonCode, ValidationJob,
)
from app.services.audit import append_audit_event
from app.services.auth import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_database(db: AsyncSession) -> dict[str, str]:
    """Seed a comprehensive demo organization into BRIDGE."""
    logger.info("Starting BRIDGE demo database seeding...")

    # Check if org already exists
    existing_org = (await db.execute(
        select(Organisation).where(Organisation.slug == "apex-global")
    )).scalar_one_or_none()

    if existing_org:
        logger.info("Apex Global organization already exists. Skipping duplicate seeding.")
        return {"status": "already_seeded", "org_id": str(existing_org.id)}

    # 1. Create Organization
    org = Organisation(
        name="Apex Global Technologies",
        slug="apex-global",
        settings={"tier": "enterprise", "features": ["continuity", "guideline_x", "audit_chain"]},
    )
    db.add(org)
    await db.flush()
    logger.info(f"Created Organisation: {org.name} ({org.id})")

    # 2. Create 5 Users across all system roles
    default_pw_hash = hash_password("password123")
    user_specs = [
        ("admin@bridge.local", "Alexander Vance", UserRole.administrator),
        ("brand_manager@bridge.local", "Elena Rostova", UserRole.brand_manager),
        ("reviewer@bridge.local", "Marcus Chen", UserRole.reviewer),
        ("creator@bridge.local", "Sophia Patel", UserRole.creator),
        ("auditor@bridge.local", "David Kross", UserRole.auditor),
    ]

    users: dict[UserRole, User] = {}
    for email, full_name, role in user_specs:
        user = User(
            org_id=org.id,
            email=email,
            hashed_password=default_pw_hash,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        users[role] = user
        logger.info(f"Created User: {full_name} ({email}) - {role.value}")

    admin_user = users[UserRole.administrator]
    bm_user = users[UserRole.brand_manager]
    reviewer_user = users[UserRole.reviewer]
    creator_user = users[UserRole.creator]

    # Initial audit event for org setup
    await append_audit_event(
        db,
        org_id=org.id,
        event_type="ORGANISATION_INITIALIZED",
        actor=admin_user,
        resource_type="organisation",
        resource_id=str(org.id),
        diff_json={"name": org.name, "slug": org.slug},
    )

    # 3. Create Knowledge Sources with Versions and Passages
    # Source A: Brand Identity Guidelines 2026
    source_brand = KnowledgeSource(
        org_id=org.id,
        name="Apex Brand Identity Guidelines 2026",
        source_type=SourceType.document,
        description="Core visual identity, typography, logo placement rules, and voice standards.",
        is_active=True,
    )
    db.add(source_brand)
    await db.flush()

    source_brand_v1 = SourceVersion(
        source_id=source_brand.id,
        version_number=1,
        file_path="/documents/Apex_Brand_Guidelines_2026_v1.pdf",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ingestion_status=IngestionStatus.completed,
        ingested_at=datetime.now(timezone.utc),
        is_current=True,
    )
    db.add(source_brand_v1)
    await db.flush()
    source_brand.current_version_id = source_brand_v1.id
    await db.flush()

    passages_brand = [
        "1.1 Logo Clearspace: The Apex symbol and logotype require a minimum clearspace equal to 24px or 'X-height' on all sides. Under no circumstances may the Apex logo appear on a red background (#FF0000 to #C00000).",
        "2.4 Typography Hierarchy: Primary brand font is Inter for digital interfaces and editorial headlines. Secondary monospace font is JetBrains Mono for telemetry readouts and code blocks.",
        "3.2 Voice & Tone: Apex speaks with quiet confidence, precision, and clarity. Avoid jargon, hyperbolic superlatives, and disruptive buzzwords like 'synergy' or 'game-changing paradigm'.",
    ]
    passage_brand_objs: list[Passage] = []
    char_offset = 0
    for idx, text in enumerate(passages_brand):
        p = Passage(
            org_id=org.id,
            source_id=source_brand.id,
            version_id=source_brand_v1.id,
            passage_index=idx,
            text=text,
            char_start=char_offset,
            char_end=char_offset + len(text),
        )
        db.add(p)
        await db.flush()
        passage_brand_objs.append(p)
        char_offset += len(text) + 20

    # Source B: Product Specifications 2026
    source_prod = KnowledgeSource(
        org_id=org.id,
        name="Apex Enterprise Cloud Platform Specifications",
        source_type=SourceType.document,
        description="Verified technical capabilities, performance metrics, compliance certifications, and SLA benchmarks.",
        is_active=True,
    )
    db.add(source_prod)
    await db.flush()

    source_prod_v1 = SourceVersion(
        source_id=source_prod.id,
        version_number=1,
        file_path="/documents/Apex_Enterprise_Specs_v1.pdf",
        file_hash="9f83c60517b4a02fb602713fcd524d4b29381e03c025ecd3ca7ab037e0e32e0c",
        ingestion_status=IngestionStatus.completed,
        ingested_at=datetime.now(timezone.utc),
        is_current=False,
    )
    db.add(source_prod_v1)
    await db.flush()

    # Source B v2 (Represents a newly released version for continuity change simulation)
    source_prod_v2 = SourceVersion(
        source_id=source_prod.id,
        version_number=2,
        file_path="/documents/Apex_Enterprise_Specs_v2.pdf",
        file_hash="b7f2029e8471b058c42b08a901049c669e2cb03e4c49d2ce892aa82a32fa859a",
        ingestion_status=IngestionStatus.completed,
        ingested_at=datetime.now(timezone.utc),
        is_current=True,
    )
    db.add(source_prod_v2)
    await db.flush()
    source_prod.current_version_id = source_prod_v2.id
    await db.flush()

    passages_prod = [
        "4.1 SLA & Latency: Apex Enterprise delivers 99.995% uptime availability across all tier-1 regions, with p99 API response latency guaranteed under 45ms.",
        "4.2 Benchmarked Efficiency: Internal customer telemetry confirms Apex automated governance reduces manual review cycles by 70% within the first 60 days of deployment.",
        "5.3 Encryption Standards: All customer data in transit is encrypted using TLS 1.3 with AES-256-GCM cipher suites. In-flight payload hashing uses SHA-256 tamper-evident chains.",
    ]
    passage_prod_objs: list[Passage] = []
    char_offset = 0
    for idx, text in enumerate(passages_prod):
        p = Passage(
            org_id=org.id,
            source_id=source_prod.id,
            version_id=source_prod_v2.id,
            passage_index=idx,
            text=text,
            char_start=char_offset,
            char_end=char_offset + len(text),
        )
        db.add(p)
        await db.flush()
        passage_prod_objs.append(p)
        char_offset += len(text) + 20

    # 4. Approved Knowledge Items (Facts, Claims, Rules, Guidelines)
    item_definitions = [
        (
            source_brand.id,
            ItemType.rule,
            "Logo Placement & Clear Space Rules",
            "The Apex primary logo must maintain a minimum clearspace of 24px and must NEVER be placed over red backgrounds (#FF0000 to #C00000).",
            bm_user.id,
        ),
        (
            source_brand.id,
            ItemType.guideline,
            "Brand Voice: Clarity and Modesty",
            "Brand communications must favor empirical clarity and quiet confidence. Disallowed terms include: 'revolutionary', 'game-changing paradigm', 'synergistic disruption'.",
            bm_user.id,
        ),
        (
            source_prod.id,
            ItemType.claim,
            "70% Review Cycle Reduction Metric",
            "Apex automated brand governance reduces multi-tier review cycle turnaround times by 70% compared to legacy manual sign-offs.",
            admin_user.id,
        ),
        (
            source_prod.id,
            ItemType.fact,
            "Enterprise API Latency & 99.995% SLA Benchmark",
            "Apex Enterprise Cloud Platform guarantees 99.995% uptime availability with sub-45ms p99 latency in all tier-1 multi-cloud regions.",
            admin_user.id,
        ),
    ]

    knowledge_items: list[KnowledgeItem] = []
    item_versions: list[ItemVersion] = []

    for s_id, itype, title, content, reviewer_id in item_definitions:
        k_item = KnowledgeItem(
            org_id=org.id,
            source_id=s_id,
            item_type=itype,
            title=title,
            created_by=reviewer_id,
        )
        db.add(k_item)
        await db.flush()

        i_ver = ItemVersion(
            item_id=k_item.id,
            version_number=1,
            content=content,
            status=ItemStatus.approved,
            created_by=reviewer_id,
            reviewed_by=reviewer_id,
            reviewed_at=datetime.now(timezone.utc),
            review_note="Verified against authoritative 2026 specs and brand guide.",
        )
        db.add(i_ver)
        await db.flush()

        k_item.current_version_id = i_ver.id
        await db.flush()

        knowledge_items.append(k_item)
        item_versions.append(i_ver)

        # Audit event for each approved item
        await append_audit_event(
            db,
            org_id=org.id,
            event_type="KNOWLEDGE_ITEM_APPROVED",
            actor=bm_user,
            resource_type="knowledge_item",
            resource_id=str(k_item.id),
            diff_json={"title": title, "version": 1, "status": "approved"},
        )

    # 5. Sample Validation Jobs, Findings, Citations & Evidence Receipts
    # Job 1: Completed validation with multiple findings (Brand violation, factual claim, tone issue)
    val_job_1 = ValidationJob(
        org_id=org.id,
        content_title="Q1 Global Marketing Campaign Brief",
        content_text=(
            "Apex Enterprise is pleased to introduce our revolutionary new cloud suite that guarantees "
            "complete synergistic transformation! With our 70% reduction in governance turnaround, "
            "marketing teams deploy faster than ever. The featured banner presents the Apex logo on a vibrant red gradient."
        ),
        status=JobStatus.completed,
        ai_provider_used="gemini-1.5-pro",
        submitted_by=creator_user.id,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(val_job_1)
    await db.flush()

    # Finding 1: Unsupported / Brand Violation (High Severity)
    finding_1 = Finding(
        job_id=val_job_1.id,
        org_id=org.id,
        finding_type=FindingType.brand_violation,
        severity=FindingSeverity.high,
        description="Prohibited logo background: The campaign banner places the Apex logo over a red gradient (#FF0000 - #C00000), violating section 1.1.",
        is_evidence_backed=True,
        status=FindingStatus.confirmed,
    )
    db.add(finding_1)
    await db.flush()

    cite_1 = FindingCitation(
        finding_id=finding_1.id,
        item_version_id=item_versions[0].id,
        passage_id=passage_brand_objs[0].id,
        exact_quote="Under no circumstances may the Apex logo appear on a red background (#FF0000 to #C00000).",
        passage_text_at_citation=passage_brand_objs[0].text,
    )
    db.add(cite_1)

    receipt_1 = EvidenceReceipt(
        finding_id=finding_1.id,
        generated_at=datetime.now(timezone.utc),
        receipt_json={
            "receipt_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rule_id": str(knowledge_items[0].id),
            "rule_title": knowledge_items[0].title,
            "violation_segment": "The featured banner presents the Apex logo on a vibrant red gradient.",
            "source_doc": "Apex Brand Identity Guidelines 2026",
            "passage_index": 0,
            "verification_confidence": 0.98,
            "deterministic_rule_matched": "PROHIBITED_COLOR_PAIRING_RED",
        },
    )
    db.add(receipt_1)

    # Finding 2: Factual Claim Supported (Info Severity)
    finding_2 = Finding(
        job_id=val_job_1.id,
        org_id=org.id,
        finding_type=FindingType.factual_claim,
        severity=FindingSeverity.info,
        description="Factual claim verified: '70% reduction in governance turnaround' is backed by Section 4.2 of Product Specifications.",
        is_evidence_backed=True,
        status=FindingStatus.confirmed,
    )
    db.add(finding_2)
    await db.flush()

    cite_2 = FindingCitation(
        finding_id=finding_2.id,
        item_version_id=item_versions[2].id,
        passage_id=passage_prod_objs[1].id,
        exact_quote="Apex automated governance reduces manual review cycles by 70% within the first 60 days of deployment.",
        passage_text_at_citation=passage_prod_objs[1].text,
    )
    db.add(cite_2)

    receipt_2 = EvidenceReceipt(
        finding_id=finding_2.id,
        generated_at=datetime.now(timezone.utc),
        receipt_json={
            "receipt_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rule_id": str(knowledge_items[2].id),
            "rule_title": knowledge_items[2].title,
            "verified_claim": "70% reduction in governance turnaround",
            "source_doc": "Apex Enterprise Cloud Platform Specifications",
            "passage_index": 1,
            "verification_confidence": 0.99,
            "status": "fully_supported",
        },
    )
    db.add(receipt_2)

    # Finding 3: Tone Issue (Medium Severity)
    finding_3 = Finding(
        job_id=val_job_1.id,
        org_id=org.id,
        finding_type=FindingType.tone_issue,
        severity=FindingSeverity.medium,
        description="Brand voice guideline breach: Contains forbidden hyperbolic terms 'revolutionary' and 'synergistic transformation'.",
        is_evidence_backed=True,
        status=FindingStatus.pending,
    )
    db.add(finding_3)
    await db.flush()

    cite_3 = FindingCitation(
        finding_id=finding_3.id,
        item_version_id=item_versions[1].id,
        passage_id=passage_brand_objs[2].id,
        exact_quote="Disallowed terms include: 'revolutionary', 'game-changing paradigm', 'synergistic disruption'.",
        passage_text_at_citation=passage_brand_objs[2].text,
    )
    db.add(cite_3)

    receipt_3 = EvidenceReceipt(
        finding_id=finding_3.id,
        generated_at=datetime.now(timezone.utc),
        receipt_json={
            "receipt_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rule_id": str(knowledge_items[1].id),
            "rule_title": knowledge_items[1].title,
            "flagged_tokens": ["revolutionary", "synergistic"],
            "recommendation": "Replace with clear empirical descriptors such as 'high-throughput' or 'orchestrated'.",
        },
    )
    db.add(receipt_3)

    # Job 2: Validated content with an Overridden Finding
    val_job_2 = ValidationJob(
        org_id=org.id,
        content_title="Partner Summit Keynote Deck Excerpt",
        content_text=(
            "In extreme enterprise deployment scenarios, Apex guarantees 99.995% availability with high resiliency. "
            "Our hybrid edge architectures allow custom exception routing."
        ),
        status=JobStatus.completed,
        ai_provider_used="gemini-1.5-pro",
        submitted_by=creator_user.id,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(val_job_2)
    await db.flush()

    finding_4 = Finding(
        job_id=val_job_2.id,
        org_id=org.id,
        finding_type=FindingType.guideline_breach,
        severity=FindingSeverity.low,
        description="Potential ambiguity regarding 'extreme enterprise deployment' qualifier.",
        is_evidence_backed=False,
        status=FindingStatus.overridden,
        override_reason_code=OverrideReasonCode.context_exception,
        override_reason_text="Keynote oral script approved for executive summit context under partner NDA.",
        overridden_by=reviewer_user.id,
        overridden_at=datetime.now(timezone.utc),
    )
    db.add(finding_4)
    await db.flush()

    await append_audit_event(
        db,
        org_id=org.id,
        event_type="FINDING_OVERRIDDEN",
        actor=reviewer_user,
        resource_type="finding",
        resource_id=str(finding_4.id),
        diff_json={
            "finding_id": str(finding_4.id),
            "reason_code": OverrideReasonCode.context_exception.value,
            "reason_text": finding_4.override_reason_text,
        },
    )

    # 6. Dependency Graph Edges (Confirmed and Possible)
    edge_1 = DependencyEdge(
        org_id=org.id,
        content_identifier="content://marketing/q1-campaign-brief",
        content_title="Q1 Global Marketing Campaign Brief",
        item_id=knowledge_items[0].id,  # Logo rule
        edge_type=EdgeType.confirmed,
        confirmed_by=bm_user.id,
        confirmed_at=datetime.now(timezone.utc),
        notes="Asset includes visual hero logo and header.",
    )
    edge_2 = DependencyEdge(
        org_id=org.id,
        content_identifier="content://marketing/q1-campaign-brief",
        content_title="Q1 Global Marketing Campaign Brief",
        item_id=knowledge_items[2].id,  # 70% claim
        edge_type=EdgeType.confirmed,
        confirmed_by=bm_user.id,
        confirmed_at=datetime.now(timezone.utc),
        notes="Cites the 70% cycle reduction metric.",
    )
    edge_3 = DependencyEdge(
        org_id=org.id,
        content_identifier="content://web/landing-page-hero",
        content_title="Apex Official Homepage Hero Banner",
        item_id=knowledge_items[3].id,  # SLA fact
        edge_type=EdgeType.confirmed,
        confirmed_by=bm_user.id,
        confirmed_at=datetime.now(timezone.utc),
        notes="Displays 99.995% SLA guarantee badge.",
    )
    edge_4 = DependencyEdge(
        org_id=org.id,
        content_identifier="content://sales/enterprise-datasheet",
        content_title="Enterprise Solution Datasheet 2026",
        item_id=knowledge_items[3].id,  # SLA fact
        edge_type=EdgeType.possible,
        notes="Inferred reference to latency benchmarks in table 3.",
    )
    edge_5 = DependencyEdge(
        org_id=org.id,
        content_identifier="content://social/linkedin-campaign-v1",
        content_title="LinkedIn Ad: Accelerate Governance",
        item_id=knowledge_items[1].id,  # Tone guideline
        edge_type=EdgeType.possible,
        notes="Ad copy tone check queued.",
    )
    for edge in [edge_1, edge_2, edge_3, edge_4, edge_5]:
        db.add(edge)
    await db.flush()

    # 7. Continuity Change Event, Impact Report & Revalidation Tasks
    change_event = ChangeEvent(
        org_id=org.id,
        source_id=source_prod.id,
        old_version_id=source_prod_v1.id,
        new_version_id=source_prod_v2.id,
        changed_by=admin_user.id,
        change_summary="Updated Enterprise Specs from v1 to v2: Refined SLA latency guarantee from 50ms to 45ms and updated compliance clause.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(change_event)
    await db.flush()

    impact_report = ImpactReport(
        change_event_id=change_event.id,
        org_id=org.id,
        affected_content_count=2,
        blast_radius_score=78.5,
        generated_at=datetime.now(timezone.utc),
        report_json={
            "direct_dependencies_count": 2,
            "indirect_dependencies_count": 3,
            "blast_radius_rating": "HIGH",
            "modified_passages": [
                {"passage_index": 0, "change": "Latency specification tightened to 45ms"}
            ],
            "affected_assets": [
                {"content_id": "content://web/landing-page-hero", "priority": "high", "exposure": 95.0},
                {"content_id": "content://sales/enterprise-datasheet", "priority": "medium", "exposure": 62.0},
            ],
        },
    )
    db.add(impact_report)
    await db.flush()

    # Revalidation tasks generated from impact report
    task_1 = RevalidationTask(
        impact_report_id=impact_report.id,
        org_id=org.id,
        content_identifier="content://web/landing-page-hero",
        content_title="Apex Official Homepage Hero Banner",
        priority=RevalidationPriority.high,
        exposure_score=95.0,
        status=RevalidationStatus.pending,
        assigned_to=reviewer_user.id,
    )
    task_2 = RevalidationTask(
        impact_report_id=impact_report.id,
        org_id=org.id,
        content_identifier="content://sales/enterprise-datasheet",
        content_title="Enterprise Solution Datasheet 2026",
        priority=RevalidationPriority.medium,
        exposure_score=62.0,
        status=RevalidationStatus.in_progress,
        assigned_to=bm_user.id,
    )
    db.add(task_1)
    db.add(task_2)
    await db.flush()

    await append_audit_event(
        db,
        org_id=org.id,
        event_type="CONTINUITY_IMPACT_CALCULATED",
        actor=admin_user,
        resource_type="impact_report",
        resource_id=str(impact_report.id),
        diff_json={"blast_radius": 78.5, "affected_count": 2},
    )

    # 8. GuidelineX: Review Signals, Ambiguity Analysis & Guideline Recommendation
    signal_1 = ReviewSignal(
        org_id=org.id,
        item_id=knowledge_items[1].id,  # Brand voice guideline
        source_type=SignalSourceType.override,
        signal_text="Creators frequently override the guideline when describing executive summits as 'disruptive industry milestones'.",
        severity=SignalSeverity.medium,
        created_by=reviewer_user.id,
        created_at=datetime.now(timezone.utc),
    )
    signal_2 = ReviewSignal(
        org_id=org.id,
        item_id=knowledge_items[1].id,
        source_type=SignalSourceType.reviewer_comment,
        signal_text="Clarification required: Does the prohibition of 'synergistic' also apply to technical descriptions of API integrations and ecosystem partners?",
        severity=SignalSeverity.high,
        created_by=reviewer_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(signal_1)
    db.add(signal_2)
    await db.flush()

    ambiguity_analysis = AmbiguityAnalysis(
        org_id=org.id,
        item_id=knowledge_items[1].id,
        trigger_signal_count=2,
        analysis_summary=(
            "Analysis of 14 recent reviewer overrides reveals high semantic friction around technical vs. marketing buzzwords. "
            "Technical architecture teams require specific vocabulary for interoperability without being penalized for marketing hype."
        ),
        ambiguous_aspects_json={
            "conflicting_contexts": [
                "Technical architecture documentation vs. consumer advertising",
                "Executive event themes vs. daily editorial copywriting"
            ],
            "friction_score": 0.84,
            "recommended_action": "Carve out technical terminology exemption"
        },
        confidence_score=0.91,
        analyzed_at=datetime.now(timezone.utc),
        ai_provider_used="gemini-1.5-pro",
    )
    db.add(ambiguity_analysis)
    await db.flush()

    recommendation = GuidelineRecommendation(
        org_id=org.id,
        item_id=knowledge_items[1].id,
        analysis_id=ambiguity_analysis.id,
        proposed_content=(
            "Brand communications must favor empirical clarity and quiet confidence. Disallowed marketing buzzwords "
            "include: 'revolutionary', 'game-changing paradigm', 'synergistic disruption'. Note: Technical interoperability "
            "terms (e.g. 'cross-system integration', 'ecosystem synergy') are permitted exclusively in whitepapers and technical specs."
        ),
        rationale="Disambiguates technical systems terminology from marketing superlatives, preventing spurious override churn.",
        status=RecommendationStatus.pending,
        created_at=datetime.now(timezone.utc),
    )
    db.add(recommendation)
    await db.flush()

    await append_audit_event(
        db,
        org_id=org.id,
        event_type="GUIDELINE_RECOMMENDATION_GENERATED",
        actor=None,
        resource_type="guideline_recommendation",
        resource_id=str(recommendation.id),
        diff_json={"item_id": str(knowledge_items[1].id), "confidence": 0.91},
    )

    await db.commit()
    logger.info("Successfully committed all BRIDGE demo data!")
    return {
        "status": "success",
        "org_id": str(org.id),
        "admin_email": "admin@bridge.local",
        "default_password": "password123",
    }


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await seed_database(session)
        print("SEEDING RESULT:", result)


if __name__ == "__main__":
    asyncio.run(main())

