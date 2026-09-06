"""Pure, deterministic Anomaly Agent formulas (FR-014, spec section 18).

No LLM, no ML model - every check here is plain statistics over a project's
own historical monthly series (rolling baseline mean/stdev -> z-score for
the latest delta), mirroring the shape of `health/formulas.py` but framed as
"is this month's change unusual relative to this project's own history?"
rather than "what is the current absolute level?" - the two are deliberately
distinct inputs to the Phase 9 Risk Fusion (spec section 23 lists "Health
Indicators" and "Anomalies" as separate items).

A z-score is only computed when there are enough prior deltas to form a
baseline (`MIN_BASELINE_POINTS`) - with too little history, the check is
skipped entirely rather than producing a fabricated score from noise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from statistics import mean, pstdev

from app.services.features.formulas import ObservationPoint, months_between

MIN_BASELINE_POINTS = 3
Z_SCORE_THRESHOLDS: list[tuple[float, str]] = [(3.0, "CRITICAL"), (2.5, "HIGH"), (2.0, "MODERATE")]
Z_SCORE_MAX_FOR_SCORE = 4.0  # score = min(|z| / this, 1.0)

STAGNANT_EPSILON = 0.01
STAGNANT_MONTHS_FOR_FLAG = 3
STAGNANT_SEVERITY_THRESHOLDS: list[tuple[int, str]] = [(6, "CRITICAL"), (3, "HIGH")]

DIVERGENCE_JUMP_THRESHOLDS: list[tuple[float, str]] = [(30.0, "CRITICAL"), (20.0, "HIGH"), (12.0, "MODERATE")]
DIVERGENCE_JUMP_MAX_FOR_SCORE = 40.0

SCHEDULE_DETERIORATION_THRESHOLDS: list[tuple[float, str]] = [
    (25.0, "CRITICAL"),
    (15.0, "HIGH"),
    (8.0, "MODERATE"),
]
SCHEDULE_DETERIORATION_MAX_FOR_SCORE = 35.0

EXPENDITURE_ACCELERATION = "EXPENDITURE_ACCELERATION"
SUDDEN_PROGRESS_DECLINE = "SUDDEN_PROGRESS_DECLINE"
PROGRESS_STAGNATION = "PROGRESS_STAGNATION"
EXPENDITURE_PROGRESS_DIVERGENCE = "EXPENDITURE_PROGRESS_DIVERGENCE"
SCHEDULE_DETERIORATION = "SCHEDULE_DETERIORATION"
UNEXPECTED_MILESTONE_CHANGES = "UNEXPECTED_MILESTONE_CHANGES"

ALL_ANOMALY_TYPES = [
    EXPENDITURE_ACCELERATION,
    SUDDEN_PROGRESS_DECLINE,
    PROGRESS_STAGNATION,
    EXPENDITURE_PROGRESS_DIVERGENCE,
    SCHEDULE_DETERIORATION,
    UNEXPECTED_MILESTONE_CHANGES,
]


@dataclass(frozen=True)
class Anomaly:
    anomaly_type: str
    severity: str  # MODERATE | HIGH | CRITICAL
    score: float  # 0.0-1.0
    description: str
    month: date


def _tier_for(value: float, thresholds: list[tuple[float, str]]) -> str | None:
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return None


def _zscore(latest: float, baseline: list[float]) -> float | None:
    if len(baseline) < MIN_BASELINE_POINTS:
        return None
    sigma = pstdev(baseline)
    if sigma <= 1e-9:
        return None
    return (latest - mean(baseline)) / sigma


def _deltas(values: list[float | None]) -> list[float]:
    return [b - a for a, b in pairwise(values) if a is not None and b is not None]


def _expected_progress(point: ObservationPoint, month: date) -> float | None:
    if point.start_date is None or point.target_completion_date is None:
        return None
    planned = months_between(point.start_date, point.target_completion_date)
    if not planned:
        return None
    elapsed = months_between(point.start_date, month)
    return 100 * elapsed / planned


def _progress_gap_series(history: list[ObservationPoint]) -> list[float]:
    gaps = []
    for point in history:
        if point.physical_progress_percent is None:
            continue
        expected = _expected_progress(point, point.month)
        if expected is None:
            continue
        gaps.append(point.physical_progress_percent - expected)
    return gaps


def _divergence_series(history: list[ObservationPoint]) -> list[float]:
    divergences = []
    for point in history:
        if (
            point.cumulative_expenditure_crore is None
            or point.physical_progress_percent is None
            or not (point.original_cost_crore or 0) > 0
        ):
            continue
        cost_utilisation = 100 * point.cumulative_expenditure_crore / point.original_cost_crore
        divergences.append(cost_utilisation - point.physical_progress_percent)
    return divergences


def _detect_zscore_anomaly(
    deltas: list[float], anomaly_type: str, month: date, description_fmt: str, positive: bool
) -> Anomaly | None:
    if len(deltas) < MIN_BASELINE_POINTS + 1:
        return None
    latest, baseline = deltas[-1], deltas[:-1]
    z = _zscore(latest, baseline)
    if z is None:
        return None
    if positive and z < Z_SCORE_THRESHOLDS[-1][0]:
        return None
    if not positive and -z < Z_SCORE_THRESHOLDS[-1][0]:
        return None
    severity = _tier_for(abs(z), Z_SCORE_THRESHOLDS)
    if severity is None:
        return None
    return Anomaly(
        anomaly_type=anomaly_type,
        severity=severity,
        score=round(min(abs(z) / Z_SCORE_MAX_FOR_SCORE, 1.0), 4),
        description=description_fmt.format(latest=latest, z=z),
        month=month,
    )


def detect_expenditure_acceleration(history: list[ObservationPoint]) -> Anomaly | None:
    deltas = _deltas([p.cumulative_expenditure_crore for p in history])
    if not deltas or deltas[-1] <= 0:
        return None
    return _detect_zscore_anomaly(
        deltas,
        EXPENDITURE_ACCELERATION,
        history[-1].month,
        "Monthly expenditure increased by ₹{latest:,.2f} Cr, {z:.1f} standard deviations above this "
        "project's own historical monthly change.",
        positive=True,
    )


def detect_sudden_progress_decline(history: list[ObservationPoint]) -> Anomaly | None:
    deltas = _deltas([p.physical_progress_percent for p in history])
    if not deltas or deltas[-1] >= 0:
        return None
    return _detect_zscore_anomaly(
        deltas,
        SUDDEN_PROGRESS_DECLINE,
        history[-1].month,
        "Physical progress changed by {latest:.1f} points, {z:.1f} standard deviations below this "
        "project's own historical monthly change.",
        positive=False,
    )


def detect_progress_stagnation(history: list[ObservationPoint]) -> Anomaly | None:
    deltas = _deltas([p.physical_progress_percent for p in history])
    consecutive = 0
    for delta in reversed(deltas):
        if abs(delta) <= STAGNANT_EPSILON:
            consecutive += 1
        else:
            break
    if consecutive < STAGNANT_MONTHS_FOR_FLAG:
        return None
    severity = _tier_for(consecutive, STAGNANT_SEVERITY_THRESHOLDS) or "MODERATE"
    return Anomaly(
        anomaly_type=PROGRESS_STAGNATION,
        severity=severity,
        score=round(min(consecutive / 10, 1.0), 4),
        description=f"Physical progress has not changed for {consecutive} consecutive observed months.",
        month=history[-1].month,
    )


def detect_expenditure_progress_divergence(history: list[ObservationPoint]) -> Anomaly | None:
    series = _divergence_series(history)
    if len(series) < 2:
        return None
    jump = series[-1] - series[-2]
    if jump <= 0:
        return None
    severity = _tier_for(jump, DIVERGENCE_JUMP_THRESHOLDS)
    if severity is None:
        return None
    return Anomaly(
        anomaly_type=EXPENDITURE_PROGRESS_DIVERGENCE,
        severity=severity,
        score=round(min(jump / DIVERGENCE_JUMP_MAX_FOR_SCORE, 1.0), 4),
        description=(
            f"Expenditure-vs-progress divergence jumped by {jump:.1f} points in a single month "
            f"(spending is accelerating relative to physical progress)."
        ),
        month=history[-1].month,
    )


def detect_schedule_deterioration(history: list[ObservationPoint]) -> Anomaly | None:
    series = _progress_gap_series(history)
    if len(series) < MIN_BASELINE_POINTS + 1:
        return None
    latest, baseline = series[-1], series[:-1]
    worsening = mean(baseline) - latest  # positive = gap got more negative than its own trend
    if worsening <= 0:
        return None
    severity = _tier_for(worsening, SCHEDULE_DETERIORATION_THRESHOLDS)
    if severity is None:
        return None
    return Anomaly(
        anomaly_type=SCHEDULE_DETERIORATION,
        severity=severity,
        score=round(min(worsening / SCHEDULE_DETERIORATION_MAX_FOR_SCORE, 1.0), 4),
        description=(
            f"The schedule gap worsened by {worsening:.1f} points relative to this project's own "
            "trailing average."
        ),
        month=history[-1].month,
    )


def detect_anomalies(history: list[ObservationPoint]) -> list[Anomaly]:
    """`history` must already be point-in-time filtered by the caller (same
    contract as `health/formulas.py:compute_health`)."""
    if not history:
        return []

    detectors = [
        detect_expenditure_acceleration,
        detect_sudden_progress_decline,
        detect_progress_stagnation,
        detect_expenditure_progress_divergence,
        detect_schedule_deterioration,
    ]
    return [a for detector in detectors if (a := detector(history)) is not None]
