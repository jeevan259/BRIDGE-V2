/**
 * BRIDGE Type Definitions
 * Exact alignment with FastAPI schemas and SQLAlchemy models.
 */

// ─── User & Auth ─────────────────────────────────────────────────────────────

export type UserRole =
  | 'administrator'
  | 'brand_manager'
  | 'reviewer'
  | 'creator'
  | 'auditor';

export interface User {
  id: string;
  org_id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserList {
  items: User[];
  total: int_or_number;
  page: number;
  page_size: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

type int_or_number = number;

// ─── Knowledge Center ────────────────────────────────────────────────────────

export type SourceType = 'document' | 'url' | 'manual';
export type IngestionStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type ItemType = 'fact' | 'claim' | 'rule' | 'guideline';
export type ItemStatus = 'pending' | 'approved' | 'superseded' | 'rejected';

export interface KnowledgeSource {
  id: string;
  org_id: string;
  name: string;
  source_type: SourceType;
  description: string | null;
  is_active: boolean;
  current_version_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSourceList {
  items: KnowledgeSource[];
  total: number;
  page: number;
  page_size: number;
}

export interface SourceVersion {
  id: string;
  source_id: string;
  version_number: number;
  file_path: string | null;
  file_hash: string | null;
  ingestion_status: IngestionStatus;
  ingested_at: string | null;
  is_current: boolean;
  created_at: string;
}

export interface KnowledgeItem {
  id: string;
  org_id: string;
  source_id: string;
  item_type: ItemType;
  title: string;
  current_version_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeItemList {
  items: KnowledgeItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ItemVersion {
  id: string;
  item_id: string;
  version_number: number;
  content: string;
  status: ItemStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_at: string;
}

export interface ItemVersionReview {
  status: ItemStatus;
  review_note?: string;
}

export interface Passage {
  id: string;
  version_id: string;
  source_id: string;
  passage_index: number;
  text: string;
  char_start: number;
  char_end: number;
}

// ─── Validation Engine ───────────────────────────────────────────────────────

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';
export type FindingType =
  | 'brand_violation'
  | 'tone_issue'
  | 'factual_claim'
  | 'guideline_breach'
  | 'unsupported';

export type FindingSeverity = 'high' | 'medium' | 'low' | 'info';
export type FindingStatus = 'pending' | 'confirmed' | 'overridden' | 'dismissed';

export type OverrideReasonCode =
  | 'rule_unclear'
  | 'context_exception'
  | 'finding_incorrect'
  | 'source_not_relevant'
  | 'content_corrected'
  | 'other';

export interface ValidationJob {
  id: string;
  org_id: string;
  content_title: string | null;
  status: JobStatus;
  ai_provider_used: string | null;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface ValidationJobList {
  items: ValidationJob[];
  total: number;
  page: number;
  page_size: number;
}

export interface Finding {
  id: string;
  job_id: string;
  org_id: string;
  finding_type: FindingType;
  severity: FindingSeverity;
  description: string;
  is_evidence_backed: boolean;
  status: FindingStatus;
  override_reason_code: OverrideReasonCode | null;
  override_reason_text: string | null;
  overridden_by: string | null;
  overridden_at: string | null;
}

export interface FindingList {
  items: Finding[];
  total: number;
  page: number;
  page_size: number;
}

export interface FindingOverridePayload {
  override_reason_code: OverrideReasonCode;
  override_reason_text?: string;
}

export interface Citation {
  id: string;
  finding_id: string;
  item_version_id: string;
  passage_id: string | null;
  exact_quote: string;
  passage_text_at_citation: string;
}

export interface EvidenceReceipt {
  id: string;
  finding_id: string;
  generated_at: string;
  receipt_json: Record<string, any>;
}

// ─── Brand Continuity ────────────────────────────────────────────────────────

export type EdgeType = 'confirmed' | 'possible';
export type RevalidationPriority = 'high' | 'medium' | 'low';
export type RevalidationStatus = 'pending' | 'in_progress' | 'completed' | 'dismissed';

export interface DependencyEdge {
  id: string;
  org_id: string;
  content_identifier: string;
  content_title: string | null;
  item_id: string;
  edge_type: EdgeType;
  confirmed_by: string | null;
  confirmed_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface DependencyEdgeList {
  items: DependencyEdge[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChangeEvent {
  id: string;
  org_id: string;
  source_id: string;
  old_version_id: string | null;
  new_version_id: string;
  changed_by: string | null;
  change_summary: string | null;
  created_at: string;
}

export interface ImpactReport {
  id: string;
  change_event_id: string;
  org_id: string;
  affected_content_count: number;
  blast_radius_score: number;
  generated_at: string;
  report_json: Record<string, any>;
}

export interface RevalidationTask {
  id: string;
  impact_report_id: string;
  org_id: string;
  content_identifier: string;
  content_title: string | null;
  priority: RevalidationPriority;
  exposure_score: number;
  status: RevalidationStatus;
  assigned_to: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface RevalidationTaskList {
  items: RevalidationTask[];
  total: number;
  page: number;
  page_size: number;
}

// ─── GuidelineX ──────────────────────────────────────────────────────────────

export type SignalSourceType = 'override' | 'reviewer_comment' | 'external_feedback';
export type SignalSeverity = 'high' | 'medium' | 'low';
export type RecommendationStatus = 'pending' | 'approved' | 'rejected';

export interface ReviewSignal {
  id: string;
  org_id: string;
  item_id: string;
  source_type: SignalSourceType;
  signal_text: string;
  severity: SignalSeverity;
  created_by: string | null;
  created_at: string;
}

export interface ReviewSignalList {
  items: ReviewSignal[];
  total: number;
  page: number;
  page_size: number;
}

export interface AmbiguityAnalysis {
  id: string;
  org_id: string;
  item_id: string;
  trigger_signal_count: number;
  analysis_summary: string;
  ambiguous_aspects_json: Record<string, any>;
  confidence_score: number;
  analyzed_at: string;
  ai_provider_used: string | null;
}

export interface GuidelineRecommendation {
  id: string;
  org_id: string;
  item_id: string;
  analysis_id: string;
  proposed_content: string;
  rationale: string | null;
  status: RecommendationStatus;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  created_at: string;
}

export interface GuidelineRecommendationList {
  items: GuidelineRecommendation[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Audit & Governance ──────────────────────────────────────────────────────

export interface AuditEvent {
  id: string;
  org_id: string;
  event_type: string;
  actor_id: string | null;
  actor_email: string;
  resource_type: string | null;
  resource_id: string | null;
  diff_json: Record<string, any> | null;
  prev_hash: string | null;
  event_hash: string;
  created_at: string;
}

export interface AuditEventList {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditVerifyResponse {
  is_valid: boolean;
  valid?: boolean;
  total_events: number;
  checked_count?: number;
  first_broken_seq?: number | null;
  broken_at: string | null;
  message: string;
}

// ─── Dashboard Stats ─────────────────────────────────────────────────────────

export interface DashboardStats {
  knowledge_items: {
    total: number;
    approved: number;
  };
  active_findings: {
    total: number;
    high_severity: number;
  };
  pending_tasks: {
    total: number;
    pending: number;
    in_progress: number;
  };
  revalidation_queue: {
    total: number;
  };
}

