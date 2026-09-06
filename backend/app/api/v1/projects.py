from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import NotFoundError
from app.repositories.project_repository import get_project, list_all_projects
from app.schemas.common import ApiResponse, success
from app.schemas.health import HealthResponse, MilestoneHealthResponse, RecentTrendResponse
from app.schemas.history import HistoryResponse
from app.schemas.prediction import PredictionRequest, PredictionResponse, ProjectSummary
from app.schemas.anomaly import AnomalyResultResponse
from app.schemas.diagnosis import DiagnosisResponse
from app.schemas.intervention import InterventionResponse
from app.schemas.rag import ReviewEvidenceResponse
from app.schemas.web import WebIntelligenceResponse
from app.services.anomaly.service import AnomalyResult, get_project_anomalies
from app.services.diagnosis.service import DiagnosisResult, diagnose_project
from app.services.health.formulas import HealthVector
from app.services.health.service import get_project_health
from app.services.history.service import DEFAULT_QUESTION, HistoryResult, get_project_history
from app.services.prediction.service import predict_cost_overrun
from app.services.intervention.service import InterventionResult, recommend_interventions
from app.services.rag.service import DEFAULT_QUESTION as DEFAULT_REVIEW_QUESTION
from app.services.rag.service import EvidenceResult, search_review_evidence
from app.services.web.service import WebIntelligenceResult, get_web_intelligence

router = APIRouter(prefix="/projects", tags=["projects"])


# Lightweight agency → sector mapping (sector column is NULL in the DB for
# all existing projects, so we infer it from the agency name).
_AGENCY_SECTOR_MAP: list[tuple[str, str]] = [
    ("POWERGRID", "Power"),
    ("NTPC", "Power"),
    ("NHPC", "Power"),
    ("Power Grid", "Power"),
    ("Airport Authority", "Aviation"),
    ("AAI", "Aviation"),
    ("NHAI", "Roads"),
    ("National Highways", "Roads"),
    ("Indian Railways", "Railways"),
    ("IRCON", "Railways"),
    ("Coal India", "Coal"),
    ("GAIL", "Petroleum & Natural Gas"),
    ("ONGC", "Petroleum & Natural Gas"),
    ("SAIL", "Steel"),
    ("Telecom", "Telecom"),
]


def _infer_sector(agency: str | None) -> str | None:
    """Best-effort sector from the agency string."""
    if not agency:
        return None
    upper = agency.upper()
    for keyword, sector in _AGENCY_SECTOR_MAP:
        if keyword.upper() in upper:
            return sector
    return "Other"


def _to_summary(project) -> ProjectSummary:
    # Determine sector: prefer the DB column, fall back to inference.
    sector = project.sector or _infer_sector(project.agency)

    # Latest observation's cumulative expenditure (observations are
    # eagerly loaded and ordered by month ascending, so last is latest).
    cumulative_expenditure: float | None = None
    if project.observations:
        latest_obs = project.observations[-1]
        cumulative_expenditure = latest_obs.cumulative_expenditure_crore

    return ProjectSummary(
        project_id=project.project_id,
        project_name=project.project_name,
        agency=project.agency,
        state=project.state,
        sector=sector,
        original_cost_crore=project.original_cost_crore,
        revised_cost_crore=project.revised_cost_crore,
        cumulative_expenditure_crore=cumulative_expenditure,
        first_observation_month=project.first_observation_month,
        latest_observation_month=project.latest_observation_month,
        observation_count=project.observation_count,
    )


@router.get("", response_model=ApiResponse)
def list_projects(request: Request, db: Session = Depends(get_db)) -> ApiResponse:
    projects = list_all_projects(db)
    data = [_to_summary(p).model_dump(mode="json") for p in projects]
    return success(data=data, trace_id=getattr(request.state, "trace_id", None))


@router.get("/{project_id}", response_model=ApiResponse)
def get_project_detail(project_id: str, request: Request, db: Session = Depends(get_db)) -> ApiResponse:
    project = get_project(db, project_id)
    if project is None:
        raise NotFoundError(f"project {project_id} not found")
    return success(
        data=_to_summary(project).model_dump(mode="json"),
        trace_id=getattr(request.state, "trace_id", None),
    )


@router.post("/{project_id}/predict", response_model=ApiResponse)
def predict(
    project_id: str, body: PredictionRequest, request: Request, db: Session = Depends(get_db)
) -> ApiResponse:
    result = predict_cost_overrun(db, project_id, body.prediction_date)
    response = PredictionResponse(**result.__dict__)
    return success(
        data=response.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None)
    )


def _to_health_response(project_id: str, vector: HealthVector) -> HealthResponse:
    return HealthResponse(
        project_id=project_id,
        snapshot_month=vector.snapshot_month,
        overall_health=vector.overall_health,
        cost_utilisation=vector.cost_utilisation,
        schedule_utilisation=vector.schedule_utilisation,
        physical_progress=vector.physical_progress,
        expected_progress=vector.expected_progress,
        progress_gap=vector.progress_gap,
        expenditure_progress_divergence=vector.expenditure_progress_divergence,
        recent_trend=RecentTrendResponse(**vector.recent_trend.__dict__),
        milestone_health=MilestoneHealthResponse(**vector.milestone_health.__dict__),
    )


@router.get("/{project_id}/health", response_model=ApiResponse)
def get_health(
    project_id: str,
    request: Request,
    as_of: date | None = Query(default=None, description="Defaults to the project's latest observed month"),
    db: Session = Depends(get_db),
) -> ApiResponse:
    if as_of is None:
        project = get_project(db, project_id)
        if project is None:
            raise NotFoundError(f"project {project_id} not found")
        if project.latest_observation_month is None:
            raise NotFoundError(f"project {project_id} has no observations")
        as_of = project.latest_observation_month

    vector = get_project_health(db, project_id, as_of)
    response = _to_health_response(project_id, vector)
    return success(
        data=response.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None)
    )


def _to_anomaly_response(result: AnomalyResult) -> AnomalyResultResponse:
    return AnomalyResultResponse(
        project_id=result.project_id,
        snapshot_month=result.snapshot_month,
        anomalies=[a.__dict__ for a in result.anomalies],
        unavailable_types=result.unavailable_types,
        input_observation_count=result.input_observation_count,
    )


@router.get("/{project_id}/anomalies", response_model=ApiResponse)
def get_anomalies(
    project_id: str,
    request: Request,
    as_of: date | None = Query(default=None, description="Defaults to the project's latest observed month"),
    db: Session = Depends(get_db),
) -> ApiResponse:
    if as_of is None:
        project = get_project(db, project_id)
        if project is None:
            raise NotFoundError(f"project {project_id} not found")
        if project.latest_observation_month is None:
            raise NotFoundError(f"project {project_id} has no observations")
        as_of = project.latest_observation_month

    result = get_project_anomalies(db, project_id, as_of)
    response = _to_anomaly_response(result)
    return success(
        data=response.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None)
    )


def _to_history_response(result: HistoryResult) -> HistoryResponse:
    return HistoryResponse(
        project_id=result.project_id,
        project_name=result.project_name,
        as_of_date=result.as_of_date,
        question=result.question,
        timeline=[e.__dict__ for e in result.timeline],
        major_changes=[c.__dict__ for c in result.major_changes],
        current_state=result.current_state,
        historical_risk_signals=[s.__dict__ for s in result.historical_risk_signals],
        summary_source=result.summary_source,
        summary_model=result.summary_model,
    )


@router.get("/{project_id}/history", response_model=ApiResponse)
def get_history(
    project_id: str,
    request: Request,
    question: str = Query(default=DEFAULT_QUESTION, description='e.g. "What happened to this project?"'),
    as_of: date | None = Query(default=None, description="Defaults to the project's latest observed month"),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = get_project_history(db, project_id, as_of_date=as_of, question=question)
    response = _to_history_response(result)
    return success(
        data=response.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None)
    )


def _to_review_evidence_response(result: EvidenceResult) -> ReviewEvidenceResponse:
    return ReviewEvidenceResponse(
        project_id=result.project_id,
        project_name=result.project_name,
        question=result.question,
        answer=result.answer,
        citations=[c.__dict__ for c in result.citations],
        summary_source=result.summary_source,
        summary_model=result.summary_model,
        evidence_found=result.evidence_found,
        searched_at=result.searched_at,
    )


@router.get("/{project_id}/review-evidence", response_model=ApiResponse)
def get_review_evidence(
    project_id: str,
    request: Request,
    question: str = Query(
        default=DEFAULT_REVIEW_QUESTION,
        description='e.g. "What does the latest review report say about this project?"',
    ),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = search_review_evidence(db, project_id, question=question)
    response = _to_review_evidence_response(result)
    return success(
        data=response.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None)
    )


def _to_web_intelligence_response(result: WebIntelligenceResult) -> WebIntelligenceResponse:
    return WebIntelligenceResponse(
        project_id=result.project_id,
        project_name=result.project_name,
        triggered=result.triggered,
        trigger_reason=result.trigger_reason,
        topics_searched=result.topics_searched,
        evidence=[
            {
                "evidence_id": e.evidence_id,
                "topic": e.topic,
                "source": e.source,
                "url": e.url,
                "title": e.title,
                "publication_date": e.publication_date,
                "date_confidence": e.date_confidence,
                "finding": e.finding,
                "project_relevance": e.project_relevance,
                "source_quality": e.source_quality,
            }
            for e in result.evidence
        ],
        warnings=result.warnings,
        searched_at=result.searched_at,
    )


@router.get("/{project_id}/web-evidence", response_model=ApiResponse)
def get_web_evidence(
    project_id: str,
    request: Request,
    force: bool = Query(default=False, description="Force a web search even if risk is not currently high"),
    as_of: date | None = Query(default=None, description="Defaults to the project's latest observed month"),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = get_web_intelligence(db, project_id, as_of_date=as_of, force=force)
    response = _to_web_intelligence_response(result)
    return success(
        data=response.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None)
    )


def _to_diagnosis_response(result: DiagnosisResult) -> DiagnosisResponse:
    return DiagnosisResponse(
        project_id=result.project_id,
        project_name=result.project_name,
        as_of_date=result.as_of_date,
        overall_risk=result.overall_risk,
        risk_score=result.risk_score,
        confidence=result.confidence,
        fusion_version=result.fusion_version,
        drivers=[d.__dict__ for d in result.drivers],
        evidence=[e.__dict__ for e in result.evidence],
    )


@router.get("/{project_id}/diagnosis", response_model=ApiResponse)
def get_diagnosis(
    project_id: str,
    request: Request,
    as_of: date | None = Query(default=None, description="Defaults to the project's latest observed month"),
    include_web: bool = Query(default=True, description="Include Phase 8 web evidence (for_diagnosis=true)"),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = diagnose_project(db, project_id, as_of_date=as_of, include_web=include_web)
    response = _to_diagnosis_response(result)
    return success(
        data=response.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None)
    )


def _to_intervention_response(result: InterventionResult) -> InterventionResponse:
    return InterventionResponse(
        project_id=result.project_id,
        project_name=result.project_name,
        as_of_date=result.as_of_date,
        overall_risk=result.overall_risk,
        suggested_monitoring_level=result.suggested_monitoring_level,
        recommendations=[r.__dict__ for r in result.recommendations],
    )


@router.get("/{project_id}/interventions", response_model=ApiResponse)
def get_interventions(
    project_id: str,
    request: Request,
    as_of: date | None = Query(default=None, description="Defaults to the project's latest observed month"),
    include_web: bool = Query(default=True, description="Include Phase 8 web evidence (for_diagnosis=true)"),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = recommend_interventions(db, project_id, as_of_date=as_of, include_web=include_web)
    response = _to_intervention_response(result)
    return success(
        data=response.model_dump(mode="json"), trace_id=getattr(request.state, "trace_id", None)
    )
