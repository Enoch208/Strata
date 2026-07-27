export type FindingLabel =
  | "confirmed_change"
  | "correction"
  | "potential_tension"
  | "consistent_statement"
  | "new_information"
  | "insufficient_evidence"
  | "needs_review";

export type RelationType =
  | "repeats"
  | "expands"
  | "revises"
  | "explicitly_corrects"
  | "disputes"
  | "contextualizes";

export type Confidence = "high" | "medium" | "low";
export type SupportStatus =
  | "supported"
  | "partially_supported"
  | "not_established";
export type ChallengeOutcome = "unchanged" | "qualified" | "revised";
export type InvestigationState =
  | "searching"
  | "retrieving"
  | "comparing"
  | "building"
  | "complete"
  | "insufficient_evidence"
  | "failed";
export type ClaimType =
  | "launch_date"
  | "delay_reason"
  | "repair_plan"
  | "test_plan"
  | "status_update"
  | "measurement"
  | "correction"
  | "other";
export type ClaimStatus =
  | "planned"
  | "scheduled"
  | "delayed"
  | "scrubbed"
  | "under_repair"
  | "testing"
  | "rolled_back"
  | "ready"
  | "launched"
  | "unknown";
export type Certainty = "explicit" | "implied" | "uncertain";
export type ArchiveIndexStatus = "ready" | "indexing" | "partial" | "failed";
export type ReelState = "idle" | "generating" | "complete" | "failed";

export interface Health {
  status: string;
  videodb: "connected" | "unavailable" | "unconfigured";
  archive_indexed: boolean;
  index_status?: string;
  detail?: string;
}

export interface ArchiveVideo {
  video_id: string;
  slug: string;
  title: string;
  source_organization: string;
  source_url: string;
  source_date: string;
  duration_seconds: number;
  index_status: string;
}

export interface Archive {
  archive_id: string;
  title: string;
  stats: {
    claim_event_count: number;
    status_change_count: number;
    video_count: number;
    indexed_duration_seconds: number;
  };
  stats_sources: {
    claim_events: string;
    status_changes: string;
    media: string;
  };
  stats_generated_at: string;
  date_range: { start: string; end: string };
  index_status: ArchiveIndexStatus;
  indexed_duration_label: string;
  videos: ArchiveVideo[];
  acknowledgement: string;
  index_version: string | null;
  manifest_version: string;
}

export interface SourcedSentence {
  sentence_id: string;
  text: string;
  supported_by_event_ids: string[];
  support_status: SupportStatus;
  is_comparative: boolean;
  lock_reason: string | null;
}

export interface Finding {
  finding_id: string;
  label: FindingLabel;
  title: string;
  summary: string;
  event_ids: string[];
  confidence: Confidence;
  review_reason: string | null;
}

export interface Relation {
  relation_id: string;
  schema_version: string;
  from_event_id: string;
  to_event_id: string;
  relation_type: RelationType;
  explanation: string;
  supporting_event_ids: string[];
  confidence: Confidence;
  review_required: boolean;
}

export interface ClaimEvent {
  event_id: string;
  schema_version: string;
  video_id: string;
  start: number;
  end: number;
  source_date: string;
  speaker_name: string | null;
  speaker_role: string | null;
  subject: string;
  claim_type: ClaimType;
  claim_text: string;
  normalized_value: string | null;
  unit: string | null;
  status: ClaimStatus;
  reason: string | null;
  certainty: Certainty;
  source_artifact_ids: string[];
  extraction_model: string;
  source_organization: string;
}

export interface Shot {
  event_id: string;
  video_id: string;
  video_title: string;
  source_url: string;
  source_date: string;
  start: number;
  end: number;
  stream_url: string | null;
  player_url: string | null;
  transcript_text: string;
}

export interface RejectedCandidate {
  event_id: string;
  reason: string;
}

export interface ChallengeResult {
  challenge_id: string;
  schema_version: string;
  prompt: string;
  initial_queries: string[];
  counter_queries: string[];
  accepted_finding_ids: string[];
  rejected_candidates: RejectedCandidate[];
  initial_accepted_video_ids: string[];
  challenge_accepted_video_ids: string[];
  novel_accepted_video_ids: string[];
  found_counter_evidence: boolean;
  outcome: ChallengeOutcome;
  impact_summary_sentence_ids: string[];
  searched_at: string;
}

export interface ReelRef {
  stream_url: string | null;
  player_url: string | null;
  event_ids: string[];
  duration_seconds: number | null;
  error: string | null;
}

export interface Investigation {
  investigation_id: string;
  archive_id: string;
  query: string;
  state: InvestigationState;
  created_at: string;
  initial_queries: string[];
  summary_sentences: SourcedSentence[];
  findings: Finding[];
  relations: Relation[];
  events: ClaimEvent[];
  shots: Shot[];
  challenge: ChallengeResult | null;
  reel: ReelRef;
  insufficient_evidence_reason: string | null;
  error: string | null;
}

export interface MetricProof {
  numerator: number;
  denominator: number;
  percentage: number | null;
}

export interface EvaluationArmProof {
  arm: "naive" | "strata";
  label: string;
  retrieval_recall: MetricProof;
  unsupported_claims: MetricProof;
}

export interface SubmissionProof {
  distinct_video_ids: number;
  index_proof: {
    spoken_word_ready: boolean;
    ocr_ready: boolean;
    visual_ready: boolean;
    claim_event_ready: boolean;
    timeline_finding_ready: boolean;
  };
  evaluation_cases: number;
  evaluation: EvaluationArmProof[];
  verification: {
    tests_passed: number;
    generated_at: string | null;
    command: string | null;
  };
}
