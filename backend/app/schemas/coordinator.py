from datetime import date

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    query: str
    project_id: str | None = None
    as_of: date | None = None


class StageResultResponse(BaseModel):
    stage: str
    status: str
    error: str | None
    duration_ms: float


class ProjectCandidateResponse(BaseModel):
    project_id: str
    project_name: str


class ReportResponse(BaseModel):
    trace_id: str
    analysis_id: str
    project_id: str
    project_name: str
    as_of_date: date
    executive_summary: str
    current_health: dict | None
    cost_overrun_risk: dict | None
    time_overrun_risk: dict | None
    key_changes: list[str]
    top_risk_drivers: list[dict]
    evidence: list[dict]
    recommended_monitoring_actions: list[dict]
    confidence: dict
    data_quality: dict
    model_versions: dict
    human_review_required: bool
    human_review_reason: str | None


class AnalysisResponse(BaseModel):
    trace_id: str
    analysis_id: str
    intent: str
    intent_source: str
    resolution_status: str | None
    project_id: str | None
    project_name: str | None
    as_of_date: date | None
    plan: list[str]
    expanded: bool
    stage_results: list[StageResultResponse]
    report: ReportResponse | None
    candidates: list[ProjectCandidateResponse]
    errors: list[str]
    warnings: list[str]


class DiagnosisSummaryResponse(BaseModel):
    overall_risk: str
    top_driver: str | None


class RankedProjectResponse(BaseModel):
    rank: int
    project_id: str
    project_name: str
    risk_score: float
    overall_health: str | None
    ml_risk_level: str | None
    ml_probability: float | None
    data_available: bool
    diagnosis_summary: DiagnosisSummaryResponse | None


class PortfolioResponse(BaseModel):
    as_of_date: date | None
    ranked: list[RankedProjectResponse]
    top_risk_project_ids: list[str]
