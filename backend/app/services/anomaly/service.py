"""Anomaly Agent service (FR-014, spec section 18) - point-in-time filtered,
same discipline as `health/service.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.project import Project, ProjectMilestone, ProjectMonthlyObservation
from app.services.anomaly.formulas import (
    ALL_ANOMALY_TYPES,
    UNEXPECTED_MILESTONE_CHANGES,
    Anomaly,
    detect_anomalies,
)
from app.services.features.formulas import ObservationPoint
from app.services.features.pipeline import filter_point_in_time, validate_point_in_time


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _to_observation_point(obs: ProjectMonthlyObservation) -> ObservationPoint:
    return ObservationPoint(
        month=obs.observation_month,
        original_cost_crore=obs.original_cost_crore,
        cumulative_expenditure_crore=obs.cumulative_expenditure_crore,
        physical_progress_percent=obs.physical_progress_percent,
        start_date=obs.start_date,
        target_completion_date=obs.target_completion_date,
    )


@dataclass(frozen=True)
class AnomalyResult:
    project_id: str
    snapshot_month: date
    anomalies: list[Anomaly]
    unavailable_types: list[str]
    input_observation_count: int


def get_project_anomalies(session: Session, project_id: str, as_of_date: date) -> AnomalyResult:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"project {project_id} not found")

    snapshot_month = _month_start(as_of_date)

    all_observations = (
        session.query(ProjectMonthlyObservation)
        .filter_by(project_id=project_id)
        .order_by(ProjectMonthlyObservation.observation_month)
        .all()
    )
    window = filter_point_in_time(all_observations, snapshot_month)
    if window:
        validate_point_in_time(window, snapshot_month)
    points = [_to_observation_point(o) for o in window]

    anomalies = detect_anomalies(points)

    # Milestones are never populated in the real source data (Phase 1/4's own
    # finding) - reported as unavailable, never fabricated.
    milestones = session.query(ProjectMilestone).filter_by(project_id=project_id).count()
    unavailable_types = [] if milestones else [UNEXPECTED_MILESTONE_CHANGES]
    assert set(unavailable_types) <= set(ALL_ANOMALY_TYPES)

    return AnomalyResult(
        project_id=project_id,
        snapshot_month=snapshot_month,
        anomalies=anomalies,
        unavailable_types=unavailable_types,
        input_observation_count=len(points),
    )
