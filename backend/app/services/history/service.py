"""Project History Agent (Phase 6) orchestration.

Workflow (matches the spec exactly):

    Project -> Monthly observations -> Milestones -> Events -> Trend detection
        -> Timeline -> LLM summary

Every stage before "LLM summary" is deterministic (Phases 1-4 + timeline.py).
The LLM only ever writes `current_state`, grounded in that finished evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.models.project import Project
from app.repositories.project_repository import (
    get_chronological_observations,
    get_data_quality_issues_for_project,
    get_project_events,
)
from app.services.health.service import get_project_health
from app.services.history.llm import SummaryResult, summarize_current_state
from app.services.history.timeline import (
    MajorChange,
    RiskSignal,
    TimelineEntry,
    build_major_changes,
    build_risk_signals,
    build_timeline,
)
from app.services.prediction.service import predict_cost_overrun

DEFAULT_QUESTION = "What happened to this project?"


@dataclass(frozen=True)
class HistoryResult:
    project_id: str
    project_name: str
    as_of_date: date
    question: str
    timeline: list[TimelineEntry]
    major_changes: list[MajorChange]
    current_state: str
    historical_risk_signals: list[RiskSignal]
    summary_source: str
    summary_model: str | None


def get_project_history(
    session: Session,
    project_id: str,
    as_of_date: date | None = None,
    question: str = DEFAULT_QUESTION,
) -> HistoryResult:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"project {project_id} not found")
    if project.latest_observation_month is None:
        raise NotFoundError(f"project {project_id} has no observations")

    as_of = as_of_date or project.latest_observation_month

    observations = get_chronological_observations(session, project_id)
    observations = [o for o in observations if o.observation_month <= as_of]
    events = [e for e in get_project_events(session, project_id) if e.event_month <= as_of]
    dq_issues = get_data_quality_issues_for_project(session, project_id)

    timeline = build_timeline(observations, events)
    major_changes = build_major_changes(events)

    health = get_project_health(session, project_id, as_of)

    ml_probability = ml_risk_level = ml_model_version = None
    try:
        prediction = predict_cost_overrun(session, project_id, as_of)
        ml_probability = prediction.probability
        ml_risk_level = prediction.risk_level
        ml_model_version = prediction.model_version
    except AppError:
        pass  # ML unavailable must not block the history agent (SRS section 24)

    risk_signals = build_risk_signals(
        dq_issues=dq_issues,
        health_snapshot_month=as_of,
        overall_health=health.overall_health,
        progress_gap=health.progress_gap,
        expenditure_progress_divergence=health.expenditure_progress_divergence,
        ml_probability=ml_probability,
        ml_risk_level=ml_risk_level,
        ml_model_version=ml_model_version,
    )

    latest_health = {
        "overall_health": health.overall_health,
        "cost_utilisation": health.cost_utilisation,
        "schedule_utilisation": health.schedule_utilisation,
        "physical_progress": health.physical_progress,
        "expected_progress": health.expected_progress,
        "progress_gap": health.progress_gap,
        "expenditure_progress_divergence": health.expenditure_progress_divergence,
        "recent_trend": health.recent_trend.label,
    }
    if project.revised_cost_crore is None or project.revised_cost_crore == project.original_cost_crore:
        latest_health["revised_cost_status"] = (
            "No revised cost is currently recorded as of the selected observation date."
        )

    settings = get_settings()
    summary: SummaryResult = summarize_current_state(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        project_name=project.project_name,
        question=question,
        timeline=timeline,
        major_changes=major_changes,
        risk_signals=risk_signals,
        latest_health=latest_health,
    )

    return HistoryResult(
        project_id=project_id,
        project_name=project.project_name,
        as_of_date=as_of,
        question=question,
        timeline=timeline,
        major_changes=major_changes,
        current_state=summary.text,
        historical_risk_signals=risk_signals,
        summary_source=summary.source,
        summary_model=summary.model,
    )
