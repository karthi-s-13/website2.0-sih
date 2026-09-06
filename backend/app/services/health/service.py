"""Project Health Service (Phase 4): deterministic, point-in-time project
condition - independent of the ML model (Phase 3) and of Phase 2's ratio-scale
feature store. No LLM involved anywhere in this module.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import DataQualityFailureError, NotFoundError
from app.models.project import Project, ProjectMilestone, ProjectMonthlyObservation
from app.services.features.formulas import ObservationPoint
from app.services.features.pipeline import filter_point_in_time, validate_point_in_time
from app.services.health.formulas import HealthVector, compute_health, compute_milestone_health


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


def get_project_health(session: Session, project_id: str, as_of_date: date) -> HealthVector:
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
    if not window:
        raise DataQualityFailureError(
            f"no observation available for project {project_id} at or before {snapshot_month.isoformat()}"
        )
    validate_point_in_time(window, snapshot_month)

    points = [_to_observation_point(o) for o in window]

    milestones = (
        session.query(ProjectMilestone)
        .filter_by(project_id=project_id)
        .filter(
            (ProjectMilestone.planned_date.is_(None)) | (ProjectMilestone.planned_date <= snapshot_month)
        )
        .all()
    )
    milestone_health = compute_milestone_health(milestones)

    return compute_health(points, snapshot_month, milestone_health)
