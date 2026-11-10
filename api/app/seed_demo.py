"""One-command demo tenant seeder for BRIDGE v2.

Fictional brand: Aurora Outdoors.
Idempotent and safe to run multiple times.
Generates natural audit events through the audit service.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

from app.ai.gemini import get_embedding_provider
from app.database import AsyncSessionLocal
from app.models.audit import AuditEvent
from app.models.continuity import (
    ChangeEvent,
    DependencyEdge,
    EdgeType,
    ImpactReport,
    RevalidationPriority,
    RevalidationStatus,
    RevalidationTask,
)
from app.models.guideline import (
    AmbiguityAnalysis,
    GuidelineRecommendation,
    RecommendationStatus,
    ReviewSignal,
    SignalSeverity,
    SignalSourceType,
)
from app.models.knowledge import (
    IngestionStatus,
    ItemStatus,
    ItemType,
    ItemVersion,
    KnowledgeItem,
    KnowledgeSource,
    Passage,
    SourceType,
    SourceVersion,
)
from app.models.organisation import Organisation
from app.models.user import User, UserRole
from app.models.validation import (
    ContentItem,
    EvidenceReceipt,
    Finding,
    FindingCitation,
    FindingSeverity,
    FindingStatus,
    FindingType,
    JobStatus,
    OverrideReasonCode,
    ValidationJob,
)
from app.services.audit import append_audit_event
from app.services.auth import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AURORA_SLUG = "aurora-outdoors"
AURORA_NAME = "Aurora Outdoors"

DEMO_USERS_INFO = [
    ("admin@aurora.local", "Alexander Vance", UserRole.administrator),
    ("brand_manager@aurora.local", "Elena Rostova", UserRole.brand_manager),
    ("reviewer@aurora.local", "Marcus Chen", UserRole.reviewer),
    ("creator@aurora.local", "Sophia Patel", UserRole.creator),
    ("auditor@aurora.local", "David Kross", UserRole.auditor),
]

PASSAGES_V1 = [
    ("1.1 Logo Clearspace", "The Aurora Outdoors primary emblem and wordmark require a minimum clearspace equal to 32px or 1.5x the height of the mountain peak symbol on all sides. No graphic elements, borders, or text may intrude into this zone."),
    ("1.2 Logo Minimum Size", "The primary logo must never be reproduced smaller than 120px wide in digital interfaces or 25mm in print. For smaller applications down to 48px, use the simplified mountain icon mark only."),
    ("1.3 Primary Brand Colors", "Aurora Outdoors primary colors are Forest Deep (#1A3A2A), Mountain Moss (#2D5A40), and Alpine Snow (#F5F9F6). These three colors must form the foundation of at least 60% of all brand surfaces."),
    ("1.4 Accent & Secondary Colors", "Secondary accents are Sunset Ochre (#E07A5F), Glacier Blue (#4A90E2), and Granite Gray (#475569). Neon, fluorescent, or saturated crimson red (#FF0000) are strictly prohibited."),
    ("2.1 Typography - Display Headlines", "Display headlines must be set in Outfit Bold or Outfit ExtraBold. Line-height should be tight (1.1x to 1.15x font size). Tracking is set to -0.02em."),
    ("2.2 Typography - Body & Copy", "Body copy must be rendered in Inter Regular or Medium with generous 1.6x line-height for legibility across outdoor lighting conditions. Minimum body size on mobile is 16px."),
    ("2.3 Monospace Telemetry", "Technical metrics, GPS coordinates, gear specifications, and elevation numbers must use JetBrains Mono or Roboto Mono in uppercase."),
    ("3.1 Voice & Tone - Grounded Elevation", "Aurora speaks with quiet confidence, rugged honesty, and technical mastery. We celebrate nature as a companion, not an adversary to conquer. We never shout."),
    ("3.2 Prohibited Hype Buzzwords", "Never use hyperbolic sales superlatives such as 'revolutionary', 'game-changing paradigm', 'disruptive transformation', or 'world's best gear' without empirical third-party test data."),
    ("3.3 Environmental Stewardship Tone", "When discussing sustainability or recycled materials, use precise verified terminology (e.g., '100% post-consumer recycled nylon, GRS certified'). Avoid vague greenwashing claims like 'eco-friendly'."),
    ("4.1 Photography Style - Natural Light", "All imagery must utilize natural outdoor lighting: golden hour, overcast mist, or alpine dawn. Studio product photography on sterile white backgrounds is strictly restricted to ecommerce catalog grids."),
    ("4.2 Photography Composition", "Human subjects in photography must appear engaged with real outdoor activities: trail running, backcountry hiking, summit bivouacs. Never stage artificial studio poses."),
    ("5.1 Accessibility - WCAG Contrast", "Text and interactive elements must satisfy WCAG 2.1 AA standards (minimum 4.5:1 contrast ratio for normal text, 3:1 for large display headers). Forest Deep on Alpine Snow satisfies AAA at 11.2:1."),
    ("5.2 Alt-Text Requirements", "All digital imagery published on web, email, or social channels must include descriptive alt text conveying the scene, gear featured, and terrain setting."),
    ("6.1 Social Media - Channel Handles", "Official social posts must tag @AuroraOutdoors and feature verified hashtags #RoamResilient and #LeaveNoTrace. Co-marketing partner logos must sit separated by a vertical divider line."),
    ("6.2 Community UGC Guidelines", "User-generated content reshared on brand channels must have explicit written permission and photo credit in the first line of the caption: 'Captured by @handle on the Pacific Crest Trail'."),
    ("7.1 Legal Disclaimers - Alpine Gear", "All packaging and ad copy featuring technical climbing harnesses, crampons, or avalanche safety probes must feature the exact statutory safety disclaimer: 'Mountaineering and backcountry travel carry inherent risk. Review manufacturer specs before use.'"),
    ("7.2 Warranty & Repair Claims", "The Aurora 'Lifetime Trail-Ready Guarantee' covers manufacturing defects for the functional life of the product. Normal wear and tear, campfire ember damage, or unauthorized modifications are covered via our repair program at cost."),
    ("8.1 Packaging & Print Substrates", "All packaging boxes must use FSC-certified unbleached kraft paperboard printed with soy-based vegetable inks. Single-use plastic wrap is prohibited."),
    ("8.2 Hangtag Placement & Fasteners", "Hangtags must be attached via recycled cotton cord or biodegradable twine through reinforced eyelets. Plastic zip-ties are banned."),
    ("9.1 Field Test Claims & Data", "Claims of thermal insulation, waterproof hydrostatic head (e.g. 20,000mm), or breathability must cite the accredited testing standard (ISO 811 or ASTM D751) and test report reference number."),
    ("9.2 Sub-Zero Temperature Ratings", "Sleeping bag and expedition parka temperature ratings must quote EN/ISO 23537 comfort ratings rather than subjective extreme limits in marketing highlights."),
    ("10.1 Co-Branding Logo Proportion", "When co-branding with expedition partners (e.g., Gore-Tex, Vibram), the Aurora emblem must remain visually dominant and separated by at least 1.5x clearspace from partner insignias."),
    ("10.2 Event & Trail Sponsorship", "Sponsored trail race or conservation event signage must display the monochrome Forest Deep logo on natural wood or recycled canvas banners."),
    ("10.3 Merchandising Apparel Placement", "On technical outerwear, the Aurora mountain logo is positioned on the left chest (maximum 60mm wide) or on the upper left sleeve. Center chest placement is prohibited on technical jackets."),
]

PASSAGES_V2 = [
    ("1.1 Logo Clearspace (v2 Updated)", "The Aurora Outdoors primary emblem and wordmark require a minimum clearspace equal to 36px (updated from 24px) or 2x the height of the mountain peak symbol on all sides. High-visibility orange (#FF6B35) may be used for technical safety gear badges."),
    ("1.4 Accent Colors (v2 Expanded)", "Secondary accents are Sunset Ochre (#E07A5F), Glacier Blue (#4A90E2), Safety Amber (#FF9F1C), and Trail Slate (#334155). Saturated primary red (#FF0000) remains prohibited."),
    ("3.1 Voice & Tone (v2 Refined)", "Aurora speaks with quiet confidence, rugged honesty, and inclusive outdoor encouragement. We embrace technical precision while welcoming outdoor novices. Avoid elitist jargon."),
]

PASSAGES_V3 = [
    ("1.1 Logo Clearspace (v3 Modern)", "The Aurora Outdoors primary emblem and wordmark require a minimum clearspace equal to 40px on digital screens and 15mm in physical packaging. Minimum resolution for digital SVG/WebP assets is 300dpi equivalent."),
    ("5.1 Accessibility - WCAG Contrast (v3 Enhanced)", "All digital color pairings must pass WCAG 2.1 AAA contrast (7:1) for body text and AA (4.5:1) for headings. Sunset Ochre text is disallowed on light backgrounds."),
]

SAMPLE_ASSET_TITLES = [
    ("Homepage Spring Launch Copy", "web"),
    ("Flash Sale Ad Banner Concept", "web"),
    ("Venture Capital Pitch Deck Slide", "press"),
    ("Summit Technical Ice Axe Packaging Slip", "packaging"),
    ("Eco-Trail Social Post Campaign", "social"),
    ("Co-Branded Trail Marathon Email Newsletter", "social"),
]


async def seed_demo_tenant(db: AsyncSession, reset: bool = False) -> dict[str, str]:
    """Seed the Aurora Outdoors demo tenant idempotently.
    
    If reset=True, clears all existing Aurora Outdoors tenant data and reseeds fresh.
    """
    logger.info("Checking for Aurora Outdoors demo tenant...")

    existing_org = (
        await db.execute(select(Organisation).where(Organisation.slug == AURORA_SLUG))
    ).scalar_one_or_none()

    if existing_org and reset:
        logger.info("Reset requested. Purging existing Aurora Outdoors tenant...")
        await db.execute(delete(Organisation).where(Organisation.id == existing_org.id))
        await db.flush()
        existing_org = None

    demo_pw = os.getenv("DEMO_PASSWORD") or getattr(settings, "demo_password", "password123")
    pw_hash = hash_password(demo_pw)

    if existing_org and not reset:
        logger.info("Aurora Outdoors organization already exists. Ensuring user passwords and assets...")
        existing_users = (
            await db.execute(select(User).where(User.org_id == existing_org.id))
        ).scalars().all()
        for u in existing_users:
            if u.email.endswith("@aurora.local"):
                u.hashed_password = pw_hash
        
        existing_assets = (await db.execute(
            select(func.count()).select_from(ContentItem).where(ContentItem.org_id == existing_org.id)
        )).scalar_one()
        if existing_assets < 6:
            existing_creator = next((u for u in existing_users if u.role == UserRole.creator), None)
            creator_id = existing_creator.id if existing_creator else None
            for idx, (title, channel) in enumerate(SAMPLE_ASSET_TITLES):
                ci_exists = (await db.execute(
                    select(ContentItem).where(ContentItem.org_id == existing_org.id, ContentItem.title == title)
                )).scalar_one_or_none()
                if not ci_exists:
                    db.add(ContentItem(
                        org_id=existing_org.id,
                        title=title,
                        content_identifier=f"asset-{idx + 1}",
                        channel=channel,
                        created_by=creator_id,
                    ))
        await db.flush()
        return {
            "status": "already_seeded",
            "org_id": str(existing_org.id),
            "org_name": existing_org.name,
            "admin_email": "admin@aurora.local",
        }

    embedder = get_embedding_provider()

    # 1. Create Organization
    org = Organisation(
        name=AURORA_NAME,
        slug=AURORA_SLUG,
    )
    db.add(org)
    await db.flush()

    # 2. Create 5 Users with standard roles
    users: dict[UserRole, User] = {}
    for email, full_name, role in DEMO_USERS_INFO:
        u = User(
            org_id=org.id,
            email=email,
            full_name=full_name,
            role=role,
            hashed_password=pw_hash,
            is_active=True,
        )
        db.add(u)
        await db.flush()
        users[role] = u

    admin = users[UserRole.administrator]
    bm = users[UserRole.brand_manager]
    reviewer = users[UserRole.reviewer]
    creator = users[UserRole.creator]
    auditor = users[UserRole.auditor]

    await append_audit_event(
        db,
        org_id=org.id,
        event_type="ORGANISATION_INITIALIZED",
        actor=admin,
        resource_type="organisation",
        resource_id=str(org.id),
        diff_json={"name": org.name, "slug": org.slug, "tier": "enterprise"},
    )

    # 3. Create Brand Book Knowledge Source with 3 Versions
    source = KnowledgeSource(
        org_id=org.id,
        name="Aurora Outdoors Master Brand Book",
        source_type=SourceType.document,
        description="Official brand standards, visual guidelines, typography, voice principles, safety disclosures, and packaging specs.",
        is_active=True,
    )
    db.add(source)
    await db.flush()

    # Version 1 (Historical)
    v1 = SourceVersion(
        source_id=source.id,
        version_number=1,
        file_path="/documents/Aurora_Brand_Book_2024_v1.pdf",
        file_hash="1111111122223333444455556666777788889999aaaabbbbccccddddeeeeffff",
        ingestion_status=IngestionStatus.completed,
        ingested_at=datetime.now(timezone.utc),
        is_current=False,
        created_by=bm.id,
    )
    db.add(v1)
    await db.flush()

    # Version 2 (Superseded)
    v2 = SourceVersion(
        source_id=source.id,
        version_number=2,
        file_path="/documents/Aurora_Brand_Book_2025_v2.pdf",
        file_hash="2222222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
        ingestion_status=IngestionStatus.completed,
        ingested_at=datetime.now(timezone.utc),
        is_current=False,
        created_by=bm.id,
    )
    db.add(v2)
    await db.flush()

    # Version 3 (Current Active)
    v3 = SourceVersion(
        source_id=source.id,
        version_number=3,
        file_path="/documents/Aurora_Brand_Book_2026_v3.pdf",
        file_hash="3333333344445555666677778888999900001111aaaabbbbccccddddeeeeffff",
        ingestion_status=IngestionStatus.completed,
        ingested_at=datetime.now(timezone.utc),
        is_current=True,
        created_by=bm.id,
    )
    db.add(v3)
    await db.flush()

    source.current_version_id = v3.id
    await db.flush()

    # Ingest Passages for v1 (the ~25 passages)
    passages_v1_objs: list[Passage] = []
    passage_specs = PASSAGES_V1 + PASSAGES_V2 + PASSAGES_V3
    embed_res = await embedder.embed([text for _, text in passage_specs])
    if embed_res.provider == "gemini" and embed_res.dimensions != 768:
        raise ValueError("Gemini embedding dimension must be 768 for this tenant")
    org.embedding_provider = "gemini" if embed_res.provider == "gemini" else "mock"
    org.embedding_model = embed_res.model
    await db.flush()

    def embedding_fields(index: int) -> dict[str, list[float] | None]:
        vector = embed_res.embeddings[index] if index < len(embed_res.embeddings) else None
        return (
            {"embedding_vector": vector, "embedding_json": None}
            if embed_res.provider == "gemini"
            else {"embedding_vector": None, "embedding_json": vector}
        )

    char_cursor = 0
    for idx, (title, text) in enumerate(PASSAGES_V1):
        p = Passage(
            org_id=org.id,
            source_id=source.id,
            version_id=v1.id,
            passage_index=idx,
            text=f"[{title}] {text}",
            char_start=char_cursor,
            char_end=char_cursor + len(text) + len(title) + 3,
            **embedding_fields(idx),
        )
        db.add(p)
        passages_v1_objs.append(p)
        char_cursor += len(p.text) + 25

    await db.flush()

    # Passages for v2 and v3
    for idx, (title, text) in enumerate(PASSAGES_V2):
        embedding_index = len(PASSAGES_V1) + idx
        p = Passage(
            org_id=org.id,
            source_id=source.id,
            version_id=v2.id,
            passage_index=idx,
            text=f"[{title}] {text}",
            char_start=0,
            char_end=len(text),
            **embedding_fields(embedding_index),
        )
        db.add(p)

    for idx, (title, text) in enumerate(PASSAGES_V3):
        embedding_index = len(PASSAGES_V1) + len(PASSAGES_V2) + idx
        p = Passage(
            org_id=org.id,
            source_id=source.id,
            version_id=v3.id,
            passage_index=idx,
            text=f"[{title}] {text}",
            char_start=0,
            char_end=len(text),
            **embedding_fields(embedding_index),
        )
        db.add(p)

    await db.flush()

    await append_audit_event(
        db,
        org_id=org.id,
        event_type="SOURCE_CREATED",
        actor=bm,
        resource_type="knowledge_source",
        resource_id=str(source.id),
        diff_json={"name": source.name, "versions": 3, "passages_v1": len(passages_v1_objs)},
    )

    # 4. Create Guideline Items across Severities (Critical..Info)
    # Includes 1 deliberate conflict and 1 supersedes chain
    items_raw = [
        # 0. Logo Clearspace (Critical)
        ("Logo Clearspace Standard", ItemType.rule, "All logos must maintain minimum 32px or 1.5x peak-height clearspace. No text or icons may infringe.", ItemStatus.approved),
        # 1. Prohibited Saturated Red (Critical)
        ("Prohibited Red Color Palette", ItemType.rule, "Pure saturated red (#FF0000) or neon red gradients are strictly prohibited on brand surfaces. Use Sunset Ochre (#E07A5F).", ItemStatus.approved),
        # 2. Typography Standard (High)
        ("Typography: Outfit & Inter", ItemType.guideline, "Headlines require Outfit Bold. Body copy requires Inter at 1.6x line-height for legibility.", ItemStatus.approved),
        # 3. Alpine Safety Warning (Critical)
        ("Statutory Alpine Safety Disclaimer", ItemType.rule, "Technical gear copy must state: 'Mountaineering and backcountry travel carry inherent risk. Review manufacturer specs before use.'", ItemStatus.approved),
        # 4. Natural Light Photography (Medium)
        ("Natural Outdoor Light Only", ItemType.guideline, "All hero and lifestyle imagery must feature authentic natural outdoor lighting. Pure white studio backdrops prohibited.", ItemStatus.approved),
        # 5. Prohibited Hype Superlatives (High) - [Vague Rule 1 for Overrides]
        ("Prohibited Hype & Marketing Buzzwords", ItemType.guideline, "Avoid buzzwords such as 'revolutionary', 'game-changing paradigm', 'synergistic transformation', or 'world's best gear'.", ItemStatus.approved),
        # 6. Environmental Stewardship Claims (High) - [Vague Rule 2 for Overrides]
        ("Stewardship Terminology & Verified Metrics", ItemType.guideline, "All sustainability claims must use certified standards (e.g. GRS, Bluesign). General terms like 'eco-friendly' are restricted without proof.", ItemStatus.approved),
        # 7. WCAG Contrast Requirement (Critical)
        ("WCAG 2.1 AA Contrast Compliance", ItemType.rule, "Digital copy must maintain at least 4.5:1 contrast against backgrounds. White on Sunset Ochre is prohibited.", ItemStatus.approved),
        # 8. Deliberate Conflict Rule (High) -> Conflicts with Natural Light Photography (#4)
        ("Studio Catalog Technical Close-ups", ItemType.guideline, "Close-up macro shots of zippers, seams, and fabric weaves should use controlled high-contrast studio ring lights on neutral backgrounds.", ItemStatus.approved),
        # 9. Superseded Rule (Old Logo Size) -> Superseded by #10
        ("Legacy Minimum Logo Size (v1)", ItemType.rule, "Minimum logo reproduction is 80px width across all mediums.", ItemStatus.superseded),
        # 10. Current Active Logo Minimum Size (v2) -> Supersedes #9
        ("Modern Minimum Logo Size & Icon Mode", ItemType.rule, "Minimum logo reproduction is 120px in digital and 25mm in print. Under 120px, use the simplified mountain icon mark only.", ItemStatus.approved),
        # 11. Co-Branding Divider Rule (Info)
        ("Co-Branding Separation Standards", ItemType.guideline, "Partner brand emblems must be separated by a vertical divider line and equal clearspace.", ItemStatus.approved),
    ]

    items: list[KnowledgeItem] = []
    versions: list[ItemVersion] = []

    for idx, (title, itype, content, status) in enumerate(items_raw):
        k = KnowledgeItem(
            org_id=org.id,
            source_id=source.id,
            item_type=itype,
            title=title,
            created_by=bm.id,
        )
        db.add(k)
        await db.flush()

        v = ItemVersion(
            item_id=k.id,
            version_number=1,
            content=content,
            status=status,
            created_by=bm.id,
            reviewed_by=bm.id,
            reviewed_at=datetime.now(timezone.utc),
            review_note="Approved during brand initialization.",
        )
        db.add(v)
        await db.flush()

        k.current_version_id = v.id
        await db.flush()

        items.append(k)
        versions.append(v)

        await append_audit_event(
            db,
            org_id=org.id,
            event_type="ITEM_CREATED",
            actor=bm,
            resource_type="knowledge_item",
            resource_id=str(k.id),
            diff_json={"title": title, "item_type": itype.value, "status": status.value},
        )

    # 5. Dependency Graph (~12 edges)
    # Using content identifiers, notes indicating relationships:
    # requires, conflicts, supersedes, informs
    edge_specs = [
        # requires
        ("content://marketing/homepage-hero", "Homepage Hero Banner & Tagline", items[0].id, EdgeType.confirmed, "requires: Logo Clearspace Standard"),
        ("content://marketing/homepage-hero", "Homepage Hero Banner & Tagline", items[1].id, EdgeType.confirmed, "requires: Prohibited Red Color Palette"),
        ("content://marketing/homepage-hero", "Homepage Hero Banner & Tagline", items[2].id, EdgeType.confirmed, "requires: Typography Outfit & Inter"),
        ("content://pack/alpine-jacket-tag", "Alpinist Gore-Tex Shell Hangtag", items[3].id, EdgeType.confirmed, "requires: Statutory Alpine Safety Disclaimer"),
        ("content://pack/alpine-jacket-tag", "Alpinist Gore-Tex Shell Hangtag", items[6].id, EdgeType.confirmed, "requires: Stewardship Terminology"),
        ("content://social/instagram-launch", "Spring Outerwear Instagram Carousel", items[4].id, EdgeType.confirmed, "requires: Natural Outdoor Light Only"),
        ("content://email/backcountry-newsletter", "The Ridgeline Dispatch Monthly Newsletter", items[5].id, EdgeType.possible, "informs: Prohibited Hype & Marketing Buzzwords"),
        ("content://web/ecommerce-product-card", "Summit Bivouac Technical Pack Page", items[7].id, EdgeType.confirmed, "requires: WCAG 2.1 AA Contrast Compliance"),
        ("content://web/ecommerce-product-card", "Summit Bivouac Technical Pack Page", items[10].id, EdgeType.confirmed, "requires: Modern Minimum Logo Size"),
        # deliberate conflict edge
        ("content://catalog/macro-zipper-details", "Technical Macro Specs Catalog 2026", items[8].id, EdgeType.possible, "conflicts: Studio Ring Lighting vs Natural Light Only (Item 4)"),
        # supersedes relationship
        ("content://archive/legacy-brand-portal", "Legacy 2024 Partner Portal", items[9].id, EdgeType.possible, "superseded: Legacy Minimum Logo Size 80px"),
        ("content://web/partner-portal", "Aurora Expedition Partner Hub", items[11].id, EdgeType.confirmed, "informs: Co-Branding Separation Standards"),
    ]

    for cid, ctitle, item_id, etype, notes in edge_specs:
        e = DependencyEdge(
            org_id=org.id,
            content_identifier=cid,
            content_title=ctitle,
            item_id=item_id,
            edge_type=etype,
            confirmed_by=bm.id if etype == EdgeType.confirmed else None,
            confirmed_at=datetime.now(timezone.utc) if etype == EdgeType.confirmed else None,
            notes=notes,
        )
        db.add(e)
    await db.flush()

    # 6. Sample Creative Assets (6 Validation Jobs: Compliant & Violating)
    sample_assets = [
        # Asset 1: Compliant Hero Banner
        (
            "Homepage Spring Launch Copy",
            "Built for the high passes and mist-covered ridgelines. The Aurora Alpinist Shell pairs GRS-certified 100% recycled nylon with quiet weatherproofing. Roam resiliently under natural alpine skies.",
            JobStatus.completed,
            [
                (FindingType.factual_claim, FindingSeverity.info, "Compliant environmental claim: Cites GRS-certified 100% recycled nylon correctly.", True, items[6], passages_v1_objs[9]),
            ],
        ),
        # Asset 2: High Severity Red Color & Logo Violation
        (
            "Flash Sale Ad Banner Concept",
            "HUGE CLEARANCE! Don't miss our legendary gear now featuring our iconic mountain logo over a vibrant neon red gradient background (#FF0000). Limited inventory!",
            JobStatus.completed,
            [
                (FindingType.brand_violation, FindingSeverity.high, "Critical Brand Violation: Uses prohibited saturated red background (#FF0000) behind logo mark.", True, items[1], passages_v1_objs[3]),
                (FindingType.brand_violation, FindingSeverity.high, "Infringes logo minimum clearspace and safe boundary standards.", True, items[0], passages_v1_objs[0]),
            ],
        ),
        # Asset 3: Tone & Superlative Buzzwords
        (
            "Venture Capital Pitch Deck Slide",
            "Aurora Outdoors is executing a revolutionary disruptive transformation that synergistically disrupts the activewear landscape with the world's best gear.",
            JobStatus.completed,
            [
                (FindingType.tone_issue, FindingSeverity.medium, "Tone Guidance Breach: Uses prohibited sales buzzwords ('revolutionary', 'disruptive transformation', 'world's best gear').", True, items[5], passages_v1_objs[8]),
            ],
        ),
        # Asset 4: Alpine Packaging Missing Disclaimer
        (
            "Summit Technical Ice Axe Packaging Slip",
            "Engineered for vertical alpine couloirs and frozen cascades. Ultra-light titanium shaft with aggressive carbon pick. Get outside and push your boundaries.",
            JobStatus.completed,
            [
                (FindingType.brand_violation, FindingSeverity.high, "Missing Mandatory Statutory Disclaimer: Technical climbing gear packaging must carry alpine risk disclosure.", True, items[3], passages_v1_objs[16]),
            ],
        ),
        # Asset 5: Unverified Greenwashing (Overridden Finding)
        (
            "Eco-Trail Social Post Campaign",
            "Our new trailhead fleece is completely eco-friendly and 100% green for Mother Earth! Join our zero-waste movement this weekend.",
            JobStatus.completed,
            [
                (FindingType.guideline_breach, FindingSeverity.high, "Unsubstantiated stewardship claim: 'completely eco-friendly' violates rule requiring certified accredited standards.", True, items[6], passages_v1_objs[9]),
            ],
        ),
        # Asset 6: In-Progress Review Job
        (
            "Co-Branded Trail Marathon Email Newsletter",
            "Aurora Outdoors and Gore-Tex unite for the 2026 Cascade Crest 100M. Tested in sub-zero alpine blizzards under EN 23537 testing standards.",
            JobStatus.running,
            [],
        ),
    ]

    for idx, (title, text, jstatus, findings_spec) in enumerate(sample_assets):
        ci = ContentItem(
            org_id=org.id,
            title=title,
            content_identifier=f"asset-{idx + 1}",
            channel="web" if idx in (0, 1) else ("press" if idx == 2 else ("packaging" if idx == 3 else "social")),
            created_by=creator.id,
        )
        db.add(ci)
        await db.flush()

        job = ValidationJob(
            org_id=org.id,
            content_title=title,
            content_text=text,
            status=jstatus,
            ai_provider_used="mock-deterministic",
            submitted_by=creator.id,
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc) if jstatus == JobStatus.completed else None,
        )
        db.add(job)
        await db.flush()

        await append_audit_event(
            db,
            org_id=org.id,
            event_type="VALIDATION_JOB_SUBMITTED",
            actor=creator,
            resource_type="validation_job",
            resource_id=str(job.id),
            diff_json={"content_title": title, "status": jstatus.value},
        )

        for ftype, fsev, fdesc, is_backed, linked_item, linked_passage in findings_spec:
            f = Finding(
                job_id=job.id,
                org_id=org.id,
                finding_type=ftype,
                severity=fsev,
                description=fdesc,
                is_evidence_backed=is_backed,
                status=FindingStatus.confirmed,
            )
            # If asset 5, simulate an override
            if "Eco-Trail" in title:
                f.status = FindingStatus.overridden
                f.override_reason_code = OverrideReasonCode.context_exception
                f.override_reason_text = "Copy reviewed and authorized under provisional marketing exception pending official Bluesign certificate."
                f.overridden_by = reviewer.id
                f.overridden_at = datetime.now(timezone.utc)

            db.add(f)
            await db.flush()

            cite = FindingCitation(
                finding_id=f.id,
                item_version_id=linked_item.current_version_id,
                passage_id=linked_passage.id,
                exact_quote=linked_passage.text[:120],
                passage_text_at_citation=linked_passage.text,
            )
            db.add(cite)

            receipt = EvidenceReceipt(
                finding_id=f.id,
                generated_at=datetime.now(timezone.utc),
                receipt_json={
                    "receipt_id": str(uuid.uuid4()),
                    "rule_id": str(linked_item.id),
                    "rule_title": linked_item.title,
                    "passage_id": str(linked_passage.id),
                    "finding_type": ftype.value,
                    "verified_by": "BRIDGE Deterministic Evaluation Engine",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            db.add(receipt)
            await db.flush()

    # 7. Pre-existing Reviewer Override Signals (~20) Clustered on 2 Vague Rules
    # Rule 1: Prohibited Hype & Marketing Buzzwords (items[5])
    # Rule 2: Stewardship Terminology & Verified Metrics (items[6])
    signal_reasons_rule1 = [
        "Reviewer override: 'Revolutionary' allowed in internal engineering summit deck.",
        "Reviewer override: Founder interview allowed 'industry transformation' quote.",
        "Reviewer override: Technical patent press release used 'disruptive weave technology'.",
        "Dispute: Marketing team argued 'world's best gear' was quoting customer review award.",
        "Reviewer override: Podcast episode caption described climber as 'revolutionary athlete'.",
        "Ambiguity: Unclear whether 'game-changing' applies to athlete achievements or products.",
        "Reviewer override: Heritage archive post referenced 1980s 'disruptive storm shell'.",
        "Reviewer override: Annual shareholder report permitted 'strategic transformation' phrasing.",
        "Dispute: Copywriter confused about permitted adjectives for summit outerwear.",
        "Reviewer override: Executive LinkedIn post approved under personal brand exception.",
    ]

    signal_reasons_rule2 = [
        "Reviewer override: 'Eco-friendly' allowed on temporary event trash bin signage.",
        "Dispute: Recycled wool sweater has 70% GRS certification, copywriter used 'sustainable'.",
        "Reviewer override: Trail cleanup day social caption used 'green outdoors' phrase.",
        "Ambiguity: Unclear if Bluesign certified dyes qualify as 'eco-conscious'.",
        "Reviewer override: Packaging insert mentioned 'mindful footprint' without certificate code.",
        "Reviewer override: Retail window display used 'protecting our wild earth'.",
        "Dispute: Field tester review quoted 'the greenest shell I have owned'.",
        "Reviewer override: Educational blog post used 'sustainable campfire tips'.",
        "Ambiguity: Clarification required on whether European PEF standards satisfy rule.",
        "Reviewer override: Internal memo allowed 'green logistics initiative'.",
    ]

    for s_text in signal_reasons_rule1:
        sig = ReviewSignal(
            org_id=org.id,
            item_id=items[5].id,
            source_type=SignalSourceType.override,
            signal_text=s_text,
            severity=SignalSeverity.medium,
            created_by=reviewer.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(sig)

    for s_text in signal_reasons_rule2:
        sig = ReviewSignal(
            org_id=org.id,
            item_id=items[6].id,
            source_type=SignalSourceType.override,
            signal_text=s_text,
            severity=SignalSeverity.high,
            created_by=reviewer.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(sig)

    await db.flush()

    # 8. Ambiguity Analysis & GuidelineX Recommendation
    analysis = AmbiguityAnalysis(
        org_id=org.id,
        item_id=items[5].id,
        trigger_signal_count=len(signal_reasons_rule1),
        analysis_summary=(
            "Synthesized 10 reviewer overrides on Prohibited Hype & Marketing Buzzwords. "
            "High semantic friction detected between marketing superlatives (prohibited) and "
            "factual sports journalism / athletic achievements (legitimate). Copywriters frequently "
            "overrode findings when quoting sponsored expedition athletes or historical brand archives."
        ),
        ambiguous_aspects_json={
            "conflicting_dimensions": [
                "Product sales claims vs. athlete biographical journalism",
                "Internal engineering technology documentation vs. retail ad copy",
            ],
            "friction_score": 0.88,
            "recommended_resolution": "Carve out editorial athlete profile exemption with required citation attribution.",
        },
        confidence_score=0.94,
        analyzed_at=datetime.now(timezone.utc),
        ai_provider_used="mock-deterministic",
    )
    db.add(analysis)
    await db.flush()

    rec = GuidelineRecommendation(
        org_id=org.id,
        item_id=items[5].id,
        analysis_id=analysis.id,
        proposed_content=(
            "Avoid buzzwords such as 'revolutionary', 'game-changing paradigm', 'synergistic transformation', "
            "or 'world's best gear' when describing products. Note: Editorial journalism, sponsored athlete "
            "profiles, and historical archive narratives may use elevated language provided quotes are attributed."
        ),
        rationale="Eliminates 75% of spurious reviewer overrides while preserving strict prohibition on commercial ad hype.",
        status=RecommendationStatus.pending,
        created_at=datetime.now(timezone.utc),
    )
    db.add(rec)
    await db.flush()

    await append_audit_event(
        db,
        org_id=org.id,
        event_type="GUIDELINE_RECOMMENDATION_GENERATED",
        actor=None,
        resource_type="guideline_recommendation",
        resource_id=str(rec.id),
        diff_json={"item_id": str(items[5].id), "confidence": 0.94},
    )

    # 9. Brand Continuity: Simulated Source Change Event & Revalidation Tasks
    change_event = ChangeEvent(
        org_id=org.id,
        source_id=source.id,
        old_version_id=v2.id,
        new_version_id=v3.id,
        changed_by=admin.id,
        change_summary="Annual Brand Book update from v2 to v3: Modernized digital clearspace to 40px, mandated WCAG AAA contrast, and clarified packaging standards.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(change_event)
    await db.flush()

    report = ImpactReport(
        change_event_id=change_event.id,
        org_id=org.id,
        affected_content_count=4,
        blast_radius_score=82.5,
        generated_at=datetime.now(timezone.utc),
        report_json={
            "direct_dependencies_count": 4,
            "blast_radius_rating": "HIGH",
            "modified_passages_count": 2,
            "affected_assets": [
                {"content_id": "content://marketing/homepage-hero", "priority": "high", "exposure": 95.0},
                {"content_id": "content://web/ecommerce-product-card", "priority": "high", "exposure": 90.0},
                {"content_id": "content://pack/alpine-jacket-tag", "priority": "medium", "exposure": 65.0},
                {"content_id": "content://web/partner-portal", "priority": "low", "exposure": 35.0},
            ],
        },
    )
    db.add(report)
    await db.flush()

    task1 = RevalidationTask(
        impact_report_id=report.id,
        org_id=org.id,
        content_identifier="content://marketing/homepage-hero",
        content_title="Homepage Hero Banner & Tagline",
        priority=RevalidationPriority.high,
        exposure_score=95.0,
        status=RevalidationStatus.pending,
        assigned_to=reviewer.id,
        created_at=datetime.now(timezone.utc),
    )
    task2 = RevalidationTask(
        impact_report_id=report.id,
        org_id=org.id,
        content_identifier="content://web/ecommerce-product-card",
        content_title="Summit Bivouac Technical Pack Page",
        priority=RevalidationPriority.high,
        exposure_score=90.0,
        status=RevalidationStatus.in_progress,
        assigned_to=bm.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(task1)
    db.add(task2)
    await db.flush()

    await append_audit_event(
        db,
        org_id=org.id,
        event_type="CONTINUITY_IMPACT_CALCULATED",
        actor=admin,
        resource_type="impact_report",
        resource_id=str(report.id),
        diff_json={"blast_radius": 82.5, "affected_count": 4},
    )

    await db.commit()
    logger.info("Successfully seeded Aurora Outdoors demo tenant!")

    return {
        "status": "success",
        "org_id": str(org.id),
        "org_name": org.name,
        "admin_email": "admin@aurora.local",
    }


async def main() -> None:
    async with AsyncSessionLocal() as session:
        res = await seed_demo_tenant(session, reset=False)
        print("SEED RESULT:", res)


if __name__ == "__main__":
    asyncio.run(main())

