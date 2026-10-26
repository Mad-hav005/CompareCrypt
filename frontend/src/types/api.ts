/**
 * API contracts mirroring backend FastAPI schemas (app.models.schemas + app.models.er_schemas).
 */

export type MatchingMode = 'comparecrypt' | 'exact' | 'comparison' | 'entity_resolution';

// Health Check Response
export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  crypto_group: string;
}

// Exact PSI
export interface ExactMatchRequest {
  alice_data: string[];
  bob_data: string[];
  normalize?: boolean;
}

export interface ExactMatchResponse {
  matches: string[];
  match_count: number;
  alice_dataset_size: number;
  bob_dataset_size: number;
  protocol_name: string;
}

// Plaintext Fuzzy Matching
export interface FuzzyMatchPair {
  alice_record: string;
  bob_record: string;
  similarity: number;
}

export interface FuzzyMatchRequest {
  alice_data: string[];
  bob_data: string[];
  threshold: number;
  normalize?: boolean;
}

export interface FuzzyMatchResponse {
  matches: FuzzyMatchPair[];
  match_count: number;
  alice_dataset_size: number;
  bob_dataset_size: number;
  threshold: number;
  policy: string;
}

// CompareCrypt (Cryptographic Shingle Threshold PSI)
export interface ThresholdMatchPair {
  alice_record_id: number;
  bob_record_id: number;
  alice_record: string;
  bob_record: string;
  intersection_count: number;
  dice_similarity: number;
  threshold: number;
  match_decision: boolean;
}

export interface ThresholdMatchRequest {
  alice_data: string[];
  bob_data: string[];
  threshold: number;
}

export interface ThresholdMatchResponse {
  matches: ThresholdMatchPair[];
  match_count: number;
  alice_dataset_size: number;
  bob_dataset_size: number;
  threshold: number;
  protocol_name: string;
}

// Unified Result for UI display
export interface UnifiedMatchRecord {
  aliceRecord: string;
  bobRecord: string;
  similarity: number;
  isMatch: boolean;
  intersectionCount?: number;
}

export interface UnifiedMatchResult {
  mode: MatchingMode;
  protocolName: string;
  aliceSize: number;
  bobSize: number;
  matchCount: number;
  threshold: number;
  executionTimeMs: number;
  estimatedPayloadKb?: number;
  matches: UnifiedMatchRecord[];
}

export type ProtocolStageId =
  | 'shingle_extraction'
  | 'alice_blinding'
  | 'bob_evaluation'
  | 'bob_digest'
  | 'alice_unblinding'
  | 'similarity_calc'
  | 'threshold_eval'
  | 'complete';

export interface ProtocolStage {
  id: ProtocolStageId;
  label: string;
  party: 'Alice' | 'Bob' | 'Alice & Bob';
  description: string;
  status: 'pending' | 'active' | 'completed';
}

// ─────────────────────────────────────────────────────────────────────────────
// Entity Resolution Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ColumnInfo {
  name: string;
  index: number;
  sample_values: string[];
  non_empty_count: number;
}

export interface DatasetSchema {
  party: string;
  filename: string;
  row_count: number;
  columns: ColumnInfo[];
  preview_rows: Record<string, string>[];
}

export type MatchStrategy = 'exact' | 'fuzzy' | 'ignore';

export interface AttributeMapping {
  column_a: string;
  column_b: string;
  strategy: MatchStrategy;
  weight: number;
  fuzzy_threshold: number;
}

export type ERJobPhase = 'queued' | 'blocking' | 'matching' | 'scoring' | 'complete' | 'error';

export interface ERJobStatus {
  job_id: string;
  phase: ERJobPhase;
  progress_pct: number;
  candidate_pairs: number;
  processed_pairs: number;
  match_count: number;
  error_message?: string;
  elapsed_ms: number;
}

export interface AttributeScore {
  column_a: string;
  column_b: string;
  strategy: MatchStrategy;
  score: number | null;
  weight: number;
}

export interface EntityMatchResult {
  row_index_a: number;
  row_index_b: number;
  overall_score: number;
  attribute_scores: AttributeScore[];
  is_match: boolean;
  row_a_preview: Record<string, string>;
  row_b_preview: Record<string, string>;
}

export interface ERJobResults {
  job_id: string;
  total_matches: number;
  total_unmatched_a: number;
  total_unmatched_b: number;
  dataset_size_a: number;
  dataset_size_b: number;
  candidate_pairs_evaluated: number;
  overall_threshold: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: EntityMatchResult[];
  protocol_notes: string;
}

export interface UploadDatasetResponse {
  job_id: string;
  party: string;
  dataset_schema: DatasetSchema;
}

export interface StartERJobRequest {
  job_id: string;
  mappings: AttributeMapping[];
  overall_threshold: number;
  normalize: boolean;
}
