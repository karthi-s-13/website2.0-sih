"""Risk Diagnosis Agent orchestration (Phase 9, spec section 24): answers
"Why is this project at risk?" by running every intelligence source built
in Phases 1-8 plus the new Anomaly module, fusing them into one evidence
pool (`app.services.evidence.fusion`), then deterministically identifying
drivers (`drivers.py`) and an overall risk score (`risk_fusion.py`).

Web/Review evidence gathering reuses Phase 7/8's own internal graceful
degradation (a failed embedding call, a failed web search, etc. already
degrade to a deterministic fallback inside those services rather than
raising) - this orchestration does not need its own try/except around them,
matching how Phase 6 already trusts Phase 3's internal robustness. The one
exception is the ML prediction, which - like Phase 6 - is wrapped in
`except AppError: pass`, since an unavailable model is a real, expected
failure mode (SRS section 24) that must not block diagnosis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.project import Project
from app.repositories.project_repository import get_data_quality_issues_for_project, get_project_events
from app.services.anomaly.formulas import MIN_BASELINE_POINTS
from app.services.anomaly.service import get_project_anomalies
from app.services.diagnosis.drivers import Driver, identify_drivers
from app.services.diagnosis.risk_fusion import fuse_risk
from app.services.evidence.fusion import FusedEvidence, fuse_evidence
from app.services.health.formulas import HealthVector
from app.services.health.service import get_project_health
from app.services.prediction.service import PredictionResult, predict_cost_overrun
from app.services.rag.service import DEFAULT_QUESTION, search_review_evidence
from app.services.web.service import get_web_intelligence


@dataclass(frozen=True)
class DiagnosisResult:
    project_id: str
    project_name: str
    as_of_date: date
    overall_risk: str
    risk_score: float | None
    confidence: float
    fusion_version: str
    drivers: list[Driver]
    evidence: list[FusedEvidence]
    # Already computed internally (needed for evidence fusion/drivers) -
    # exposed here so callers (Coordinator/Reporting) never need to
    # re-run get_project_health just to populate the report's health section.
    health: HealthVector | None = None
    # Already computed internally (needed for evidence fusion/drivers) -
    # exposed for the same reason as `health` above.
    prediction: PredictionResult | None = None


def diagnose_project(
    session: Session,
    project_id: str,
    as_of_date: date | None = None,
    include_web: bool = True,
    question: str | None = None,
) -> DiagnosisResult:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"project {project_id} not found")
    if project.latest_observation_month is None:
        raise NotFoundError(f"project {project_id} has no observations")

    as_of = as_of_date or project.latest_observation_month

    health = get_project_health(session, project_id, as_of)

    prediction = None
    try:
        prediction = predict_cost_overrun(session, project_id, as_of)
    except AppError:
        pass  # ML unavailable must not block diagnosis (SRS section 24)

    anomaly_result = get_project_anomalies(session, project_id, as_of)
    # Distinguish "detection ran and found nothing" (a real, available
    # result) from "too little history to run at all" (see risk_fusion.py).
    anomalies_for_fusion = (
        anomaly_result.anomalies
        if anomaly_result.input_observation_count >= MIN_BASELINE_POINTS + 1
        else None
    )

    events = [e for e in get_project_events(session, project_id) if e.event_month <= as_of]
    dq_issues = get_data_quality_issues_for_project(session, project_id)

    review = search_review_evidence(session, project_id, question=question or DEFAULT_QUESTION)
    web = get_web_intelligence(session, project_id, as_of_date=as_of, for_diagnosis=True) if include_web else None

    evidence = fuse_evidence(
        project_id=project_id,
        project_name=project.project_name,
        agency_code=project.agency_code,
        as_of=as_of,
        health=health,
        anomaly_result=anomaly_result,
        events=events,
        dq_issues=dq_issues,
        prediction=prediction,
        review=review,
        web=web,
    )

    drivers = identify_drivers(health, prediction, anomaly_result, evidence)
    fusion = fuse_risk(health, prediction, anomalies_for_fusion, evidence)

    return DiagnosisResult(
        project_id=project_id,
        project_name=project.project_name,
        as_of_date=as_of,
        overall_risk=fusion.overall_risk,
        risk_score=fusion.risk_score,
        confidence=fusion.confidence,
        fusion_version=fusion.fusion_version,
        drivers=drivers,
        evidence=evidence,
        health=health,
        prediction=prediction,
    )
