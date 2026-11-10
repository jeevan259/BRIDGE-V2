"""models package — imports all models so SQLAlchemy declarative registry is complete."""
from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.organisation import Organisation
from app.models.user import RefreshToken, User, UserRole
from app.models.knowledge import (
    BrandDocument, IngestionStatus, ItemStatus, ItemType,
    ItemVersion, KnowledgeItem, KnowledgePassage, KnowledgeRecord,
    KnowledgeSource, KnowledgeVersion, Passage, SourceType, SourceVersion,
)
from app.models.validation import (
    ContentItem, ContentSnapshot, EvidenceReceipt, Finding,
    FindingCitation, FindingEvidence, FindingSeverity, FindingStatus,
    FindingType, JobStatus, OverrideReasonCode, ReviewDecision,
    ValidationJob, ValidationRun,
)
from app.models.continuity import (
    ChangeEvent, DependencyEdge, EdgeType, ImpactReport,
    RevalidationPriority, RevalidationStatus, RevalidationTask,
)
from app.models.guideline import (
    AmbiguityAnalysis, GuidelineInsight, GuidelineRecommendation,
    GuidelineSignal, RecommendationStatus, ReviewSignal,
    SignalSeverity, SignalSourceType,
)
from app.models.audit import AuditEvent
from app.models.job import Job, JobQueueStatus

__all__ = [
    "Base", "TimestampMixin", "UUIDMixin",
    "Organisation",
    "User", "UserRole", "RefreshToken",
    "KnowledgeSource", "BrandDocument", "SourceVersion", "IngestionStatus",
    "KnowledgeItem", "KnowledgeRecord", "ItemType",
    "ItemVersion", "KnowledgeVersion", "ItemStatus",
    "Passage", "KnowledgePassage", "SourceType",
    "ContentItem", "ContentSnapshot", "ValidationJob", "ValidationRun",
    "Finding", "FindingType", "FindingSeverity", "FindingStatus", "OverrideReasonCode",
    "FindingCitation", "EvidenceReceipt", "FindingEvidence", "ReviewDecision", "JobStatus",
    "DependencyEdge", "EdgeType", "ChangeEvent", "ImpactReport",
    "RevalidationTask", "RevalidationPriority", "RevalidationStatus",
    "ReviewSignal", "GuidelineSignal", "SignalSourceType", "SignalSeverity",
    "AmbiguityAnalysis", "GuidelineInsight", "GuidelineRecommendation", "RecommendationStatus",
    "AuditEvent",
    "Job", "JobQueueStatus",
]
