"""Pure, deterministic project-health formulas (Phase 4).

No LLM, no ML model - every number here is a plain arithmetic calculation
over point-in-time observations, independent of both the pretrained ML
model (Phase 3) and the ratio-scale ML feature store (Phase 2). All values
are on the 0-100 percentage scale (SRS FR-008), unlike Phase 2's ratio-scale
features - the two are deliberately separate systems that happen to share
underlying concepts.

Sign conventions (fixed by the Phase 4 spec's own example: physical_progress
52.1, expected_progress 74.2, cost_utilisation 68.4 -> progress_gap -22.1,
expenditure_progress_divergence 16.3):

    progress_gap = physical_progress - expected_progress
        (negative = behind schedule)
    expenditure_progress_divergence = cost_utilisation - physical_progress
        (positive = spending ahead of physical progress)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from statistics import mean

from app.services.features.formulas import ObservationPoint, months_between

STAGNANT_EPSILON = 0.01
TREND_WINDOW_MONTHS = 3
STAGNANT_MONTHS_FOR_FLAG = 3

# Version tag for this module's formulas (Phase 12 Analytics MCP envelope:
# {"value": ..., "formula_version": ..., ...}). Phase 4 never needed its own
# version string before Analytics MCP exposed these formulas individually -
# bump this if the health calculations themselves change.
HEALTH_FORMULA_VERSION = "health-v1"

HEALTH_LEVELS: list[str] = ["NORMAL", "WATCH", "ELEVATED", "HIGH", "CRITICAL"]

# (threshold, label) pairs, checked highest-first. A value >= threshold gets
# that label; below the lowest threshold falls through to "NORMAL". Kept as
# named, documented constants (not buried magic numbers) so they can be
# retuned against historical evaluation data (Phase 14) without touching the
# calculation logic itself.
SCHEDULE_SHORTFALL_THRESHOLDS: list[tuple[float, str]] = [
    (70, "CRITICAL"),
    (50, "HIGH"),
    (30, "ELEVATED"),
    (15, "WATCH"),
]
DIVERGENCE_THRESHOLDS: list[tuple[float, str]] = [
    (60, "CRITICAL"),
    (40, "HIGH"),
    (25, "ELEVATED"),
    (10, "WATCH"),
]


@dataclass(frozen=True)
class MilestoneHealth:
    status: str  # NOT_AVAILABLE | GOOD | WATCH | POOR
    total: int
    completed: int
    delayed: int


@dataclass(frozen=True)
class RecentTrend:
    monthly_progress_change: float | None
    monthly_expenditure_change: float | None
    progress_slope: float | None  # mean of the trailing TREND_WINDOW_MONTHS progress deltas
    expenditure_slope: float | None
    consecutive_stagnant_months: int
    label: str  # IMPROVING | STABLE | STAGNANT | DECLINING | DATA_NOT_AVAILABLE


@dataclass(frozen=True)
class HealthVector:
    snapshot_month: date
    overall_health: str
    cost_utilisation: float | None
    schedule_utilisation: float | None
    physical_progress: float | None
    expected_progress: float | None
    progress_gap: float | None
    expenditure_progress_divergence: float | None
    recent_trend: RecentTrend
    milestone_health: MilestoneHealth
    input_observation_count: int


def _tier_for(value: float, thresholds: list[tuple[float, str]]) -> str:
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return "NORMAL"


def _level_index(label: str) -> int:
    return HEALTH_LEVELS.index(label)


def compute_milestone_health(milestones: list) -> MilestoneHealth:
    """Never fabricates a score when there is no milestone data - which, for
    the real Flash Report source data, is always (see Phase 1: the source
    has no milestone fields at all)."""
    if not milestones:
        return MilestoneHealth(status="NOT_AVAILABLE", total=0, completed=0, delayed=0)

    total = len(milestones)
    completed = sum(1 for m in milestones if (m.status or "").upper() == "COMPLETED")
    delayed = sum(
        1 for m in milestones if m.actual_date and m.planned_date and m.actual_date > m.planned_date
    )
    if delayed == 0:
        status = "GOOD"
    elif delayed / total <= 0.2:
        status = "WATCH"
    else:
        status = "POOR"
    return MilestoneHealth(status=status, total=total, completed=completed, delayed=delayed)


def _recent_trend(history: list[ObservationPoint], window: int) -> RecentTrend:
    progress_deltas = [
        b.physical_progress_percent - a.physical_progress_percent
        for a, b in pairwise(history)
        if a.physical_progress_percent is not None and b.physical_progress_percent is not None
    ]
    expenditure_deltas = [
        b.cumulative_expenditure_crore - a.cumulative_expenditure_crore
        for a, b in pairwise(history)
        if a.cumulative_expenditure_crore is not None and b.cumulative_expenditure_crore is not None
    ]

    if not progress_deltas:
        return RecentTrend(None, None, None, None, 0, "DATA_NOT_AVAILABLE")

    monthly_progress_change = progress_deltas[-1]
    monthly_expenditure_change = expenditure_deltas[-1] if expenditure_deltas else None
    progress_slope = mean(progress_deltas[-window:])
    expenditure_slope = mean(expenditure_deltas[-window:]) if expenditure_deltas else None

    consecutive_stagnant = 0
    for delta in reversed(progress_deltas):
        if abs(delta) <= STAGNANT_EPSILON:
            consecutive_stagnant += 1
        else:
            break

    if consecutive_stagnant >= STAGNANT_MONTHS_FOR_FLAG:
        label = "STAGNANT"
    elif progress_slope > STAGNANT_EPSILON:
        label = "IMPROVING"
    elif progress_slope < -STAGNANT_EPSILON:
        label = "DECLINING"
    else:
        label = "STABLE"

    return RecentTrend(
        monthly_progress_change=monthly_progress_change,
        monthly_expenditure_change=monthly_expenditure_change,
        progress_slope=progress_slope,
        expenditure_slope=expenditure_slope,
        consecutive_stagnant_months=consecutive_stagnant,
        label=label,
    )


def compute_health(
    history: list[ObservationPoint],
    snapshot_month: date,
    milestone_health: MilestoneHealth,
    trend_window_months: int = TREND_WINDOW_MONTHS,
) -> HealthVector:
    if not history:
        raise ValueError("history must contain at least one observation at or before snapshot_month")

    current = history[-1]

    elapsed = months_between(current.start_date, snapshot_month) if current.start_date else None
    planned = (
        months_between(current.start_date, current.target_completion_date)
        if current.start_date and current.target_completion_date
        else None
    )

    cost_utilisation = None
    if current.cumulative_expenditure_crore is not None and (current.original_cost_crore or 0) > 0:
        cost_utilisation = 100 * current.cumulative_expenditure_crore / current.original_cost_crore

    schedule_utilisation = None
    if elapsed is not None and planned not in (None, 0):
        schedule_utilisation = 100 * elapsed / planned

    physical_progress = current.physical_progress_percent
    expected_progress = schedule_utilisation

    progress_gap = None
    if physical_progress is not None and expected_progress is not None:
        progress_gap = physical_progress - expected_progress

    divergence = None
    if cost_utilisation is not None and physical_progress is not None:
        divergence = cost_utilisation - physical_progress

    recent_trend = _recent_trend(history, trend_window_months)

    tiers = []
    if progress_gap is not None:
        tiers.append(_tier_for(-progress_gap, SCHEDULE_SHORTFALL_THRESHOLDS))
    if divergence is not None:
        tiers.append(_tier_for(divergence, DIVERGENCE_THRESHOLDS))

    if not tiers:
        overall_health = "DATA_NOT_AVAILABLE"
    else:
        overall_index = max(_level_index(t) for t in tiers)
        if recent_trend.label == "STAGNANT" and overall_index < len(HEALTH_LEVELS) - 1:
            overall_index += 1
        overall_health = HEALTH_LEVELS[overall_index]

    return HealthVector(
        snapshot_month=snapshot_month,
        overall_health=overall_health,
        cost_utilisation=cost_utilisation,
        schedule_utilisation=schedule_utilisation,
        physical_progress=physical_progress,
        expected_progress=expected_progress,
        progress_gap=progress_gap,
        expenditure_progress_divergence=divergence,
        recent_trend=recent_trend,
        milestone_health=milestone_health,
        input_observation_count=len(history),
    )
