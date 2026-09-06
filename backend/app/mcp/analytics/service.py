"""Analytics MCP (Phase 12): deterministic project-health metrics (Phase 4)
and anomaly detection (Phase 9's Anomaly module) - no LLM, no ML model
anywhere in this server. `calculate_health` returns the full health vector;
the per-metric tools are thin wrappers extracting one field, in the
standard {value, formula_version, inputs, calculated_at} envelope (spec
section 37).
"""

from __future__ import annotations

from datetime import date

from mcp.server.fastmcp import FastMCP

from app.core.errors import AppError
from app.mcp._shared import now_iso, session_scope
from app.mcp.analytics.schemas import (
    AnomalyItem,
    AnomalyResponse,
    HealthResponse,
    MetricResponse,
    MilestoneHealthModel,
    RecentTrendModel,
)
from app.models.project import ProjectMonthlyObservation
from app.repositories.project_repository import get_project
from app.services.anomaly.service import get_project_anomalies
from app.services.features.formulas import EXPECTED_PROGRESS_METHOD
from app.services.features.pipeline import filter_point_in_time
from app.services.health.formulas import HEALTH_FORMULA_VERSION, TREND_WINDOW_MONTHS, HealthVector
from app.services.health.service import get_project_health

mcp = FastMCP(
    "analytics",
    instructions="Deterministic project-health metrics (Phase 4) and anomaly detection "
    "(Phase 9) - no LLM, no ML model.",
)


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _resolve_as_of(session, project_id: str, as_of_date: date | None) -> date | None:  # noqa: ANN001
    if as_of_date is not None:
        return as_of_date
    project = get_project(session, project_id)
    return project.latest_observation_month if project is not None else None


def _current_observation_raw(session, project_id: str, snapshot_month: date) -> dict:  # noqa: ANN001
    """Raw fields for a metric's `inputs`, for the metrics whose true
    mathematical inputs aren't already fields on `HealthVector` (cost/
    schedule/expected-progress utilisation). Reuses `filter_point_in_time`
    exactly as `health/service.py` does - no new point-in-time logic."""
    all_observations = (
        session.query(ProjectMonthlyObservation).filter_by(project_id=project_id)
        .order_by(ProjectMonthlyObservation.observation_month)
        .all()
    )
    window = filter_point_in_time(all_observations, snapshot_month)
    if not window:
        return {}
    current = window[-1]
    return {
        "cumulative_expenditure_crore": current.cumulative_expenditure_crore,
        "original_cost_crore": current.original_cost_crore,
        "start_date": current.start_date.isoformat() if current.start_date else None,
        "target_completion_date": current.target_completion_date.isoformat()
        if current.target_completion_date
        else None,
    }


def _health_or_error(
    session, project_id: str, as_of_date: date | None
) -> tuple[HealthVector | None, str, date | None, str | None]:  # noqa: ANN001
    """Returns (health, status, snapshot_month, message)."""
    as_of = _resolve_as_of(session, project_id, as_of_date)
    project = get_project(session, project_id)
    if project is None:
        return None, "NOT_FOUND", None, f"project {project_id} not found"
    if as_of is None:
        return None, "NOT_AVAILABLE", None, f"project {project_id} has no observations"
    try:
        health = get_project_health(session, project_id, as_of)
    except AppError as exc:
        return None, "NOT_AVAILABLE", _month_start(as_of), exc.message
    return health, "OK", health.snapshot_month, None


def _metric_response(
    session, project_id: str, as_of_date: date | None, *, value_fn, formula_version: str, inputs_fn
) -> MetricResponse:  # noqa: ANN001
    health, status, snapshot_month, message = _health_or_error(session, project_id, as_of_date)
    if health is None:
        return MetricResponse(status=status, project_id=project_id, snapshot_month=snapshot_month, message=message)
    return MetricResponse(
        status="OK",
        project_id=project_id,
        snapshot_month=health.snapshot_month,
        value=value_fn(health),
        formula_version=formula_version,
        inputs=inputs_fn(health),
        calculated_at=now_iso(),
    )


@mcp.tool()
def calculate_health(project_id: str, as_of_date: date | None = None) -> HealthResponse:
    """Full deterministic project-health vector as of as_of_date (defaults
    to the project's latest observed month)."""
    with session_scope() as session:
        health, status, snapshot_month, message = _health_or_error(session, project_id, as_of_date)
        if health is None:
            return HealthResponse(status=status, project_id=project_id, snapshot_month=snapshot_month, message=message)
        return HealthResponse(
            status="OK",
            project_id=project_id,
            snapshot_month=health.snapshot_month,
            overall_health=health.overall_health,
            cost_utilisation=health.cost_utilisation,
            schedule_utilisation=health.schedule_utilisation,
            physical_progress=health.physical_progress,
            expected_progress=health.expected_progress,
            progress_gap=health.progress_gap,
            expenditure_progress_divergence=health.expenditure_progress_divergence,
            recent_trend=RecentTrendModel(**vars(health.recent_trend)),
            milestone_health=MilestoneHealthModel(**vars(health.milestone_health)),
            input_observation_count=health.input_observation_count,
            formula_version=HEALTH_FORMULA_VERSION,
        )


@mcp.tool()
def calculate_cost_utilisation(project_id: str, as_of_date: date | None = None) -> MetricResponse:
    """Cumulative expenditure as a percentage of original approved cost."""
    with session_scope() as session:
        return _metric_response(
            session,
            project_id,
            as_of_date,
            value_fn=lambda h: h.cost_utilisation,
            formula_version=HEALTH_FORMULA_VERSION,
            inputs_fn=lambda h: _current_observation_raw(session, project_id, h.snapshot_month),
        )


@mcp.tool()
def calculate_schedule_utilisation(project_id: str, as_of_date: date | None = None) -> MetricResponse:
    """Elapsed schedule time as a percentage of planned total duration."""
    with session_scope() as session:
        return _metric_response(
            session,
            project_id,
            as_of_date,
            value_fn=lambda h: h.schedule_utilisation,
            formula_version=HEALTH_FORMULA_VERSION,
            inputs_fn=lambda h: _current_observation_raw(session, project_id, h.snapshot_month),
        )


@mcp.tool()
def calculate_progress_gap(project_id: str, as_of_date: date | None = None) -> MetricResponse:
    """physical_progress - expected_progress (negative = behind schedule)."""
    with session_scope() as session:
        return _metric_response(
            session,
            project_id,
            as_of_date,
            value_fn=lambda h: h.progress_gap,
            formula_version=HEALTH_FORMULA_VERSION,
            inputs_fn=lambda h: {"physical_progress": h.physical_progress, "expected_progress": h.expected_progress},
        )


@mcp.tool()
def calculate_divergence(project_id: str, as_of_date: date | None = None) -> MetricResponse:
    """cost_utilisation - physical_progress (positive = spending ahead of
    physical progress)."""
    with session_scope() as session:
        return _metric_response(
            session,
            project_id,
            as_of_date,
            value_fn=lambda h: h.expenditure_progress_divergence,
            formula_version=HEALTH_FORMULA_VERSION,
            inputs_fn=lambda h: {"cost_utilisation": h.cost_utilisation, "physical_progress": h.physical_progress},
        )


@mcp.tool()
def calculate_expected_progress(project_id: str, as_of_date: date | None = None) -> MetricResponse:
    """Linear expected-progress model (elapsed / planned duration), method
    id "linear-v1" per FR-009 - a different, more specific version tag than
    the other Analytics tools, since this is Phase 2's own versioned
    method, reused here rather than reinvented."""
    with session_scope() as session:
        return _metric_response(
            session,
            project_id,
            as_of_date,
            value_fn=lambda h: h.expected_progress,
            formula_version=EXPECTED_PROGRESS_METHOD,
            inputs_fn=lambda h: _current_observation_raw(session, project_id, h.snapshot_month),
        )


@mcp.tool()
def calculate_trend(project_id: str, as_of_date: date | None = None) -> MetricResponse:
    """Recent trend (progress/expenditure deltas, stagnation flag, label).
    Deliberately not a scalar `value` - the underlying concept genuinely
    isn't a single number."""
    with session_scope() as session:
        return _metric_response(
            session,
            project_id,
            as_of_date,
            value_fn=lambda h: vars(h.recent_trend),
            formula_version=HEALTH_FORMULA_VERSION,
            inputs_fn=lambda h: {"trend_window_months": TREND_WINDOW_MONTHS},
        )


@mcp.tool()
def detect_anomaly(project_id: str, as_of_date: date | None = None) -> AnomalyResponse:
    """Point-in-time z-score anomaly detection over a project's own
    historical monthly deltas (Phase 9) - expenditure acceleration, sudden
    progress decline, stagnation, expenditure/progress divergence,
    schedule deterioration."""
    with session_scope() as session:
        as_of = _resolve_as_of(session, project_id, as_of_date)
        project = get_project(session, project_id)
        if project is None:
            return AnomalyResponse(status="NOT_FOUND", project_id=project_id)
        if as_of is None:
            return AnomalyResponse(status="NOT_AVAILABLE", project_id=project_id, message="no observations")

        try:
            result = get_project_anomalies(session, project_id, as_of)
        except AppError as exc:
            return AnomalyResponse(status="NOT_AVAILABLE", project_id=project_id, message=exc.message)

        return AnomalyResponse(
            status="OK",
            project_id=project_id,
            snapshot_month=result.snapshot_month,
            anomalies=[
                AnomalyItem(
                    anomaly_type=a.anomaly_type, severity=a.severity, score=a.score,
                    description=a.description, month=a.month,
                )
                for a in result.anomalies
            ],
            unavailable_types=result.unavailable_types,
            input_observation_count=result.input_observation_count,
        )
