export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface ApiError {
  error_code: string;
  message: string;
}

export interface ApiResponse<T> {
  status: string;
  data: T | null;
  trace_id: string | null;
  timestamp: string;
  errors: ApiError[];
}

export interface ProjectSummary {
  project_id: string;
  project_name: string;
  agency: string | null;
  state: string | null;
  sector: string | null;
  original_cost_crore: number | null;
  revised_cost_crore: number | null;
  cumulative_expenditure_crore: number | null;
  first_observation_month: string | null;
  latest_observation_month: string | null;
  observation_count: number;
}

export interface PredictionResponse {
  project_id: string;
  prediction_date: string;
  risk_type: string;
  probability: number;
  risk_level: "LOW" | "MODERATE" | "ELEVATED" | "HIGH" | "CRITICAL";
  model_version: string;
  feature_version: string;
  leakage_check: string;
}

export interface RecentTrend {
  monthly_progress_change: number | null;
  monthly_expenditure_change: number | null;
  progress_slope: number | null;
  expenditure_slope: number | null;
  consecutive_stagnant_months: number;
  label: "IMPROVING" | "STABLE" | "STAGNANT" | "DECLINING" | "DATA_NOT_AVAILABLE";
}

export interface MilestoneHealth {
  status: "NOT_AVAILABLE" | "GOOD" | "WATCH" | "POOR";
  total: number;
  completed: number;
  delayed: number;
}

export interface HealthResponse {
  project_id: string;
  snapshot_month: string;
  overall_health: "NORMAL" | "WATCH" | "ELEVATED" | "HIGH" | "CRITICAL" | "DATA_NOT_AVAILABLE";
  cost_utilisation: number | null;
  schedule_utilisation: number | null;
  physical_progress: number | null;
  expected_progress: number | null;
  progress_gap: number | null;
  expenditure_progress_divergence: number | null;
  recent_trend: RecentTrend;
  milestone_health: MilestoneHealth;
}

export type EvidenceSourceType = "OBSERVED_FACT" | "INFERRED_TREND" | "MODEL_PREDICTION";

export interface TimelineEntry {
  month: string;
  title: string;
  description: string;
  source_type: EvidenceSourceType;
  evidence_ref: string;
}

export interface MajorChange {
  month: string;
  change_type: string;
  description: string;
  source_type: EvidenceSourceType;
  previous_value: string | null;
  new_value: string | null;
}

export interface RiskSignal {
  month: string;
  signal_type: string;
  description: string;
  source_type: EvidenceSourceType;
  severity: string | null;
}

export interface HistoryResponse {
  project_id: string;
  project_name: string;
  as_of_date: string;
  question: string;
  timeline: TimelineEntry[];
  major_changes: MajorChange[];
  current_state: string;
  historical_risk_signals: RiskSignal[];
  summary_source: "LLM" | "DETERMINISTIC_FALLBACK";
  summary_model: string | null;
}

export interface Citation {
  document_name: string;
  page: number;
  excerpt: string;
  score: number;
}

export interface ReviewEvidenceResponse {
  project_id: string;
  project_name: string;
  question: string;
  answer: string;
  citations: Citation[];
  summary_source: "LLM" | "DETERMINISTIC_FALLBACK";
  summary_model: string | null;
  evidence_found: boolean;
  searched_at: string;
}

export interface WebEvidenceItem {
  evidence_id: string;
  topic: string;
  source: string;
  url: string;
  title: string | null;
  publication_date: string | null;
  date_confidence: "VERIFIED" | "UNVERIFIED";
  finding: string;
  project_relevance: number;
  source_quality: "HIGH" | "MEDIUM" | "LOW" | "UNVERIFIED";
}

export interface WebIntelligenceResponse {
  project_id: string;
  project_name: string;
  triggered: boolean;
  trigger_reason: string;
  topics_searched: string[];
  evidence: WebEvidenceItem[];
  warnings: string[];
  searched_at: string;
}

export type EvidenceCategory =
  | "PAIMANA_STRUCTURED_DATA"
  | "ANALYTICAL_INFERENCE"
  | "MODEL_INFERENCE"
  | "REVIEW_REPORT"
  | "OFFICIAL_EXTERNAL_SOURCE"
  | "SECONDARY_SOURCE";

export interface FusedEvidenceItem {
  evidence_id: string;
  category: EvidenceCategory;
  description: string;
  confidence: number;
  source_label: string;
  topic: string | null;
  severity: string | null;
  month: string | null;
}

export interface RiskDriver {
  rank: number;
  driver: string;
  severity: string;
  evidence_ids: string[];
  driver_key: string;
}

export interface DiagnosisResponse {
  project_id: string;
  project_name: string;
  as_of_date: string;
  overall_risk: string;
  risk_score: number | null;
  confidence: number;
  fusion_version: string;
  drivers: RiskDriver[];
  evidence: FusedEvidenceItem[];
}

export interface Recommendation {
  priority: string;
  action_type: string;
  action: string;
  reason: string;
  evidence_ids: string[];
  review_area: string;
  driver: string;
  monitoring_level: string;
}

export interface InterventionResponse {
  project_id: string;
  project_name: string;
  as_of_date: string;
  overall_risk: string;
  suggested_monitoring_level: string;
  recommendations: Recommendation[];
}

export interface StageResultItem {
  stage: string;
  status: string;
  error: string | null;
  duration_ms: number;
}

export interface ProjectCandidateItem {
  project_id: string;
  project_name: string;
}

export interface AnalysisReport {
  trace_id: string;
  analysis_id: string;
  project_id: string;
  project_name: string;
  as_of_date: string;
  executive_summary: string;
  current_health: Record<string, unknown> | null;
  cost_overrun_risk: Record<string, unknown> | null;
  time_overrun_risk: Record<string, unknown> | null;
  key_changes: string[];
  top_risk_drivers: { rank: number; driver: string; severity: string; evidence_count: number }[];
  evidence: { evidence_id: string; category: string; description: string; confidence: number; source: string }[];
  recommended_monitoring_actions: { priority: string; action: string; action_type: string }[];
  confidence: Record<string, unknown>;
  data_quality: Record<string, unknown>;
  model_versions: Record<string, unknown>;
  human_review_required: boolean;
  human_review_reason: string | null;
}

export interface AnalysisResponse {
  trace_id: string;
  analysis_id: string;
  intent: string;
  intent_source: string;
  resolution_status: string | null;
  project_id: string | null;
  project_name: string | null;
  as_of_date: string | null;
  plan: string[];
  expanded: boolean;
  stage_results: StageResultItem[];
  report: AnalysisReport | null;
  candidates: ProjectCandidateItem[];
  errors: string[];
  warnings: string[];
}

export interface DiagnosisSummaryItem {
  overall_risk: string;
  top_driver: string | null;
}

export interface RankedProjectItem {
  rank: number;
  project_id: string;
  project_name: string;
  risk_score: number;
  overall_health: string | null;
  ml_risk_level: string | null;
  ml_probability: number | null;
  data_available: boolean;
  diagnosis_summary: DiagnosisSummaryItem | null;
}

export interface PortfolioResponse {
  as_of_date: string | null;
  ranked: RankedProjectItem[];
  top_risk_project_ids: string[];
}

export interface ModelInfo {
  model_type: string;
  model_version: string;
  feature_version: string;
  raw_feature_cols: string[];
  optimal_threshold: number;
  oof_metrics: Record<string, number>;
  trained_at: string;
  n_training_rows: number;
}

export class ApiRequestError extends Error {
  errorCode: string;
  status: number;

  constructor(status: number, errorCode: string, message: string) {
    super(message);
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body: ApiResponse<T> = await res.json();
  if (!res.ok || body.status !== "success") {
    const err = body.errors?.[0];
    throw new ApiRequestError(res.status, err?.error_code ?? "UNKNOWN", err?.message ?? "Request failed");
  }
  return body.data as T;
}

export async function getBackendHealth(): Promise<ApiResponse<{ status: string }>> {
  const res = await fetch(`${API_BASE_URL}/api/health`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Backend health check failed: ${res.status}`);
  }
  return res.json();
}

export function listProjects(): Promise<ProjectSummary[]> {
  return request<ProjectSummary[]>("/api/v1/projects");
}

export function getProjectDetail(projectId: string): Promise<ProjectSummary> {
  return request<ProjectSummary>(`/api/v1/projects/${projectId}`);
}

export function predictProject(projectId: string, predictionDate: string): Promise<PredictionResponse> {
  return request<PredictionResponse>(`/api/v1/projects/${projectId}/predict`, {
    method: "POST",
    body: JSON.stringify({ prediction_date: predictionDate }),
  });
}

export function getModelInfo(): Promise<ModelInfo> {
  return request<ModelInfo>("/api/v1/models");
}

export function getProjectHealth(projectId: string, asOf?: string): Promise<HealthResponse> {
  const query = asOf ? `?as_of=${asOf}` : "";
  return request<HealthResponse>(`/api/v1/projects/${projectId}/health${query}`);
}

export function getProjectHistory(projectId: string, question?: string): Promise<HistoryResponse> {
  const query = question ? `?question=${encodeURIComponent(question)}` : "";
  return request<HistoryResponse>(`/api/v1/projects/${projectId}/history${query}`);
}

export function getReviewEvidence(projectId: string, question?: string): Promise<ReviewEvidenceResponse> {
  const query = question ? `?question=${encodeURIComponent(question)}` : "";
  return request<ReviewEvidenceResponse>(`/api/v1/projects/${projectId}/review-evidence${query}`);
}

export function getWebEvidence(projectId: string, force?: boolean): Promise<WebIntelligenceResponse> {
  const query = force ? "?force=true" : "";
  return request<WebIntelligenceResponse>(`/api/v1/projects/${projectId}/web-evidence${query}`);
}

export function getDiagnosis(projectId: string): Promise<DiagnosisResponse> {
  return request<DiagnosisResponse>(`/api/v1/projects/${projectId}/diagnosis`);
}

export function getInterventions(projectId: string): Promise<InterventionResponse> {
  return request<InterventionResponse>(`/api/v1/projects/${projectId}/interventions`);
}

export function analyzeQuery(query: string, projectId?: string): Promise<AnalysisResponse> {
  return request<AnalysisResponse>("/api/v1/analyze", {
    method: "POST",
    body: JSON.stringify({ query, project_id: projectId || undefined }),
  });
}

export function getPortfolio(topN?: number): Promise<PortfolioResponse> {
  const query = topN ? `?top_n=${topN}` : "";
  return request<PortfolioResponse>(`/api/v1/portfolio${query}`);
}
