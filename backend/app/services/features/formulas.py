"""Pure, side-effect-free point-in-time feature formulas.

`compute_feature_vector` assumes its caller has already restricted `history`
to observations with `month <= snapshot_month` (the "Temporal Filter" pipeline
stage lives in pipeline.py, not here) - this module only computes.

Units, spelled out because two different scales are used deliberately:

  - cost_utilisation, expenditure_progress_divergence: ratios (0.0-1.0-ish,
    e.g. 0.5 = 50%), because ML-facing features are kept on a shared scale.
  - physical_progress, expected_progress, progress_gap, monthly_progress_change,
    rolling_progress_change: percentage points (0-100-ish), matching the
    source `physical_progress_percent` field directly.
  - monthly_expenditure_growth, rolling_expenditure_change,
    remaining_cost_budget_crore: absolute crore amounts.
  - expenditure_growth: a relative growth *rate* (fraction), distinct from
    monthly_expenditure_growth's absolute delta.

expected_progress uses a simple linear model (elapsed / planned duration).
This is method "linear-v1" - see FR-009: the expected-progress calculation
must be explicit and versioned, and future phases may add alternative
methods (e.g. s-curve) under a different method id without touching this one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise

EXPECTED_PROGRESS_METHOD = "linear-v1"


@dataclass(frozen=True)
class ObservationPoint:
    month: date
    original_cost_crore: float | None
    cumulative_expenditure_crore: float | None
    physical_progress_percent: float | None
    start_date: date | None
    target_completion_date: date | None


@dataclass(frozen=True)
class FeatureVector:
    snapshot_month: date
    input_observation_count: int

    cost_utilisation: float | None
    expenditure_growth: float | None
    monthly_expenditure_growth: float | None
    schedule_utilisation: float | None
    physical_progress: float | None
    expected_progress: float | None
    progress_gap: float | None
    expenditure_progress_divergence: float | None
    monthly_progress_change: float | None
    rolling_progress_change: float | None
    rolling_expenditure_change: float | None
    project_age_months: int | None
    remaining_schedule_months: int | None
    remaining_cost_budget_crore: float | None


def months_between(earlier: date, later: date) -> int:
    """Integer whole-month difference (day-of-month is ignored - all dates in
    this system are normalized to the 1st, see Phase 1 parsing)."""
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def _rolling_mean_delta(values: list[float | None], window: int) -> float | None:
    deltas = [b - a for a, b in pairwise(values) if a is not None and b is not None]
    if not deltas:
        return None
    windowed = deltas[-window:]
    return sum(windowed) / len(windowed)


def compute_feature_vector(
    history: list[ObservationPoint], snapshot_month: date, rolling_window_months: int = 3
) -> FeatureVector:
    if not history:
        raise ValueError("history must contain at least one observation at or before snapshot_month")

    current = history[-1]
    prev = history[-2] if len(history) >= 2 else None

    elapsed_duration_months = (
        months_between(current.start_date, snapshot_month) if current.start_date else None
    )
    original_duration_months = (
        months_between(current.start_date, current.target_completion_date)
        if current.start_date and current.target_completion_date
        else None
    )

    cost_utilisation = None
    if current.cumulative_expenditure_crore is not None and (current.original_cost_crore or 0) > 0:
        cost_utilisation = current.cumulative_expenditure_crore / current.original_cost_crore

    schedule_utilisation = None
    if (
        elapsed_duration_months is not None
        and original_duration_months is not None
        and original_duration_months != 0
    ):
        schedule_utilisation = elapsed_duration_months / original_duration_months

    physical_progress = current.physical_progress_percent
    expected_progress = schedule_utilisation * 100 if schedule_utilisation is not None else None

    progress_gap = None
    if physical_progress is not None and expected_progress is not None:
        progress_gap = physical_progress - expected_progress

    expenditure_progress_divergence = None
    if cost_utilisation is not None and physical_progress is not None:
        expenditure_progress_divergence = cost_utilisation - (physical_progress / 100)

    monthly_progress_change = None
    monthly_expenditure_growth = None
    expenditure_growth = None
    if prev is not None:
        if physical_progress is not None and prev.physical_progress_percent is not None:
            monthly_progress_change = physical_progress - prev.physical_progress_percent
        if (
            current.cumulative_expenditure_crore is not None
            and prev.cumulative_expenditure_crore is not None
        ):
            monthly_expenditure_growth = (
                current.cumulative_expenditure_crore - prev.cumulative_expenditure_crore
            )
            if prev.cumulative_expenditure_crore != 0:
                expenditure_growth = monthly_expenditure_growth / prev.cumulative_expenditure_crore

    rolling_progress_change = _rolling_mean_delta(
        [o.physical_progress_percent for o in history], rolling_window_months
    )
    rolling_expenditure_change = _rolling_mean_delta(
        [o.cumulative_expenditure_crore for o in history], rolling_window_months
    )

    remaining_schedule_months = None
    if elapsed_duration_months is not None and original_duration_months is not None:
        remaining_schedule_months = original_duration_months - elapsed_duration_months

    remaining_cost_budget_crore = None
    if current.original_cost_crore is not None and current.cumulative_expenditure_crore is not None:
        remaining_cost_budget_crore = current.original_cost_crore - current.cumulative_expenditure_crore

    return FeatureVector(
        snapshot_month=snapshot_month,
        input_observation_count=len(history),
        cost_utilisation=cost_utilisation,
        expenditure_growth=expenditure_growth,
        monthly_expenditure_growth=monthly_expenditure_growth,
        schedule_utilisation=schedule_utilisation,
        physical_progress=physical_progress,
        expected_progress=expected_progress,
        progress_gap=progress_gap,
        expenditure_progress_divergence=expenditure_progress_divergence,
        monthly_progress_change=monthly_progress_change,
        rolling_progress_change=rolling_progress_change,
        rolling_expenditure_change=rolling_expenditure_change,
        project_age_months=elapsed_duration_months,
        remaining_schedule_months=remaining_schedule_months,
        remaining_cost_budget_crore=remaining_cost_budget_crore,
    )
