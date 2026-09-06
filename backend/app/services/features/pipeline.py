"""Point-in-time feature pipeline (Phase 2):

    Raw Data -> Clean Data -> Temporal Filter -> Feature Engineering
        -> Point-in-Time Validation -> Feature Store

"Clean Data" is `project_monthly_observations` (Phase 1). Each stage below is
a separate, explicit function so the point-in-time guarantee is checked as
its own step rather than being implicit in the feature math.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import DataLeakageError
from app.models.feature import FeatureVersion, ProjectMonthlyFeature
from app.models.project import Project, ProjectMonthlyObservation
from app.services.features.formulas import ObservationPoint, compute_feature_vector

FEATURE_VERSION = "features-v1"
ROLLING_WINDOW_MONTHS = 3
FEATURE_VERSION_DESCRIPTION = (
    "cost_utilisation=cum_exp/original_cost (ratio); schedule_utilisation="
    "elapsed_months/original_duration_months (ratio); expected_progress=schedule_utilisation*100 "
    "(linear-v1); progress_gap=physical_progress-expected_progress (points); "
    "expenditure_progress_divergence=cost_utilisation-(physical_progress/100) (ratio); "
    "monthly_*=month-over-month delta; expenditure_growth=monthly_expenditure_growth/prev_cum_exp "
    "(relative rate); rolling_*=mean of deltas over the trailing "
    f"{ROLLING_WINDOW_MONTHS} months."
)


def ensure_feature_version(session: Session) -> None:
    if session.get(FeatureVersion, FEATURE_VERSION) is not None:
        return
    session.add(
        FeatureVersion(
            version=FEATURE_VERSION,
            description=FEATURE_VERSION_DESCRIPTION,
            rolling_window_months=ROLLING_WINDOW_MONTHS,
            expected_progress_method="linear-v1",
        )
    )
    session.flush()


def filter_point_in_time(
    observations: list[ProjectMonthlyObservation], snapshot_month: date
) -> list[ProjectMonthlyObservation]:
    """Temporal Filter stage: only observations at or before snapshot_month."""
    return [o for o in observations if o.observation_month <= snapshot_month]


def validate_point_in_time(
    observations: list[ProjectMonthlyObservation], snapshot_month: date
) -> None:
    """Point-in-Time Validation stage. Raises DataLeakageError (blocking, per
    SRS section 1 / DR-005 / FR-012) if any input observation postdates the
    snapshot. Should be unreachable given filter_point_in_time is always
    called first, but the check is kept as an explicit, independent gate
    rather than trusting the caller."""
    latest = max((o.observation_month for o in observations), default=None)
    if latest is not None and latest > snapshot_month:
        raise DataLeakageError(
            f"feature_timestamp {latest} > prediction_timestamp {snapshot_month}"
        )


def _to_observation_point(obs: ProjectMonthlyObservation) -> ObservationPoint:
    return ObservationPoint(
        month=obs.observation_month,
        original_cost_crore=obs.original_cost_crore,
        cumulative_expenditure_crore=obs.cumulative_expenditure_crore,
        physical_progress_percent=obs.physical_progress_percent,
        start_date=obs.start_date,
        target_completion_date=obs.target_completion_date,
    )


def _upsert_feature_row(
    session: Session, project_id: str, snapshot_month: date, vector
) -> None:
    existing = (
        session.query(ProjectMonthlyFeature)
        .filter_by(project_id=project_id, snapshot_month=snapshot_month, feature_version=FEATURE_VERSION)
        .first()
    )
    row = existing or ProjectMonthlyFeature(
        project_id=project_id, snapshot_month=snapshot_month, feature_version=FEATURE_VERSION
    )
    row.cost_utilisation = vector.cost_utilisation
    row.expenditure_growth = vector.expenditure_growth
    row.monthly_expenditure_growth = vector.monthly_expenditure_growth
    row.schedule_utilisation = vector.schedule_utilisation
    row.physical_progress = vector.physical_progress
    row.expected_progress = vector.expected_progress
    row.progress_gap = vector.progress_gap
    row.expenditure_progress_divergence = vector.expenditure_progress_divergence
    row.monthly_progress_change = vector.monthly_progress_change
    row.rolling_progress_change = vector.rolling_progress_change
    row.rolling_expenditure_change = vector.rolling_expenditure_change
    row.project_age_months = vector.project_age_months
    row.remaining_schedule_months = vector.remaining_schedule_months
    row.remaining_cost_budget_crore = vector.remaining_cost_budget_crore
    row.input_observation_count = vector.input_observation_count
    if existing is None:
        session.add(row)


@dataclass
class FeatureBuildSummary:
    projects_processed: int = 0
    feature_rows_upserted: int = 0


def build_features_for_project(session: Session, project: Project) -> int:
    """Computes and upserts one feature row per observed month for a project.

    Each observation's own month is used as the snapshot_month, and only that
    project's observations at or before it are used as input - i.e. feature
    generation replays the panel forward one month at a time, exactly the
    point-in-time discipline a live monthly prediction run would follow.
    """
    all_observations = (
        session.query(ProjectMonthlyObservation)
        .filter_by(project_id=project.project_id)
        .order_by(ProjectMonthlyObservation.observation_month)
        .all()
    )

    rows_written = 0
    for obs in all_observations:
        snapshot_month = obs.observation_month
        window = filter_point_in_time(all_observations, snapshot_month)
        validate_point_in_time(window, snapshot_month)

        points = [_to_observation_point(o) for o in window]
        vector = compute_feature_vector(points, snapshot_month, rolling_window_months=ROLLING_WINDOW_MONTHS)

        _upsert_feature_row(session, project.project_id, snapshot_month, vector)
        rows_written += 1

    return rows_written


def build_features(session: Session, project_ids: list[str] | None = None) -> FeatureBuildSummary:
    ensure_feature_version(session)

    query = session.query(Project)
    if project_ids is not None:
        query = query.filter(Project.project_id.in_(project_ids))
    projects = query.order_by(Project.project_id).all()

    summary = FeatureBuildSummary()
    for project in projects:
        summary.feature_rows_upserted += build_features_for_project(session, project)
        summary.projects_processed += 1

    session.commit()
    return summary
