"""Deterministic timeline/major-change/risk-signal construction (Phase 6).

Everything in this module is plain, testable Python with no LLM and no
network access - it is the "Monthly observations -> Milestones -> Events ->
Trend detection -> Timeline" part of the Project History Agent workflow. The
LLM (app/services/history/llm.py) only ever sees the *output* of this module;
it never invents facts, trends, or predictions of its own.

Every entry carries a `source_type`, one of:

    OBSERVED_FACT     - directly grounded in a raw recorded value, or a plain
                         diff between two raw values (e.g. "revised_cost
                         changed from X to Y").
    INFERRED_TREND     - a judgment that required aggregating/thresholding
                         multiple data points (health tiers, non-monotonic
                         flags, stagnation).
    MODEL_PREDICTION    - strictly the ML model's output (Phase 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

OBSERVED_FACT = "OBSERVED_FACT"
INFERRED_TREND = "INFERRED_TREND"
MODEL_PREDICTION = "MODEL_PREDICTION"

DQ_RISK_ISSUE_TYPES = {"NON_MONOTONIC_CUMULATIVE_EXPENDITURE", "NON_MONOTONIC_PHYSICAL_PROGRESS"}
CONCERNING_HEALTH_LEVELS = {"WATCH", "ELEVATED", "HIGH", "CRITICAL"}


@dataclass(frozen=True)
class TimelineEntry:
    month: date
    title: str
    description: str
    source_type: str
    evidence_ref: str


@dataclass(frozen=True)
class MajorChange:
    month: date
    change_type: str
    description: str
    source_type: str
    previous_value: str | None
    new_value: str | None


@dataclass(frozen=True)
class RiskSignal:
    month: date
    signal_type: str
    description: str
    source_type: str
    severity: str | None


def _fmt_money(value: float | None) -> str:
    return "unrecorded" if value is None else f"₹{value:,.2f} Cr"


def _fmt_pct(value: float | None) -> str:
    return "unrecorded" if value is None else f"{value:.1f}%"


def build_timeline(observations: list[Any], events: list[Any]) -> list[TimelineEntry]:
    """One OBSERVED_FACT entry per monthly observation, interleaved
    chronologically with OBSERVED_FACT entries for derived field-transition
    events (e.g. a cost revision)."""
    entries: list[TimelineEntry] = []

    for obs in observations:
        entries.append(
            TimelineEntry(
                month=obs.observation_month,
                title="Monthly observation recorded",
                description=(
                    f"Cumulative expenditure {_fmt_money(obs.cumulative_expenditure_crore)}; "
                    f"physical progress {_fmt_pct(obs.physical_progress_percent)}."
                    + (f" Note: {obs.notes}" if getattr(obs, "notes", None) else "")
                ),
                source_type=OBSERVED_FACT,
                evidence_ref=f"project_monthly_observations:{obs.observation_month.isoformat()}",
            )
        )

    for ev in events:
        entries.append(
            TimelineEntry(
                month=ev.event_month,
                title=ev.event_type.replace("_", " ").title(),
                description=ev.description,
                source_type=OBSERVED_FACT,
                evidence_ref=f"project_events:{ev.event_type}:{ev.event_month.isoformat()}",
            )
        )

    entries.sort(key=lambda e: (e.month, e.source_type != OBSERVED_FACT))
    return entries


def build_major_changes(events: list[Any]) -> list[MajorChange]:
    """Field-transition events that represent a genuine change from a prior
    state - excludes PROJECT_FIRST_OBSERVED, which is an origin point, not a
    change."""
    return [
        MajorChange(
            month=ev.event_month,
            change_type=ev.event_type,
            description=ev.description,
            source_type=OBSERVED_FACT,
            previous_value=ev.previous_value,
            new_value=ev.new_value,
        )
        for ev in events
        if ev.event_type != "PROJECT_FIRST_OBSERVED"
    ]


def build_risk_signals(
    dq_issues: list[Any],
    health_snapshot_month: date,
    overall_health: str | None,
    progress_gap: float | None,
    expenditure_progress_divergence: float | None,
    ml_probability: float | None,
    ml_risk_level: str | None,
    ml_model_version: str | None,
) -> list[RiskSignal]:
    signals: list[RiskSignal] = []

    for issue in dq_issues:
        if issue.issue_type not in DQ_RISK_ISSUE_TYPES:
            continue
        month = _issue_month(issue)
        signals.append(
            RiskSignal(
                month=month,
                signal_type=issue.issue_type,
                description=(
                    f"{issue.field} did not increase as expected "
                    f"(recorded value: {issue.original_value})."
                ),
                source_type=INFERRED_TREND,
                severity=issue.severity,
            )
        )

    if overall_health in CONCERNING_HEALTH_LEVELS:
        driver = (
            f"progress is {abs(progress_gap):.1f} points behind expected schedule"
            if progress_gap is not None and progress_gap < 0
            else "expenditure is running ahead of physical progress"
            if expenditure_progress_divergence is not None and expenditure_progress_divergence > 0
            else "deterministic health indicators crossed a concern threshold"
        )
        signals.append(
            RiskSignal(
                month=health_snapshot_month,
                signal_type="HEALTH_TIER",
                description=f"Overall health is {overall_health}: {driver}.",
                source_type=INFERRED_TREND,
                severity=overall_health,
            )
        )

    if ml_probability is not None:
        signals.append(
            RiskSignal(
                month=health_snapshot_month,
                signal_type="ML_COST_OVERRUN_PROBABILITY",
                description=(
                    f"Model {ml_model_version} estimates a {ml_probability * 100:.1f}% probability of "
                    f"future cost overrun ({ml_risk_level} risk level). This is a forward-looking "
                    "risk estimate, not a confirmed outcome."
                ),
                source_type=MODEL_PREDICTION,
                severity=ml_risk_level,
            )
        )

    signals.sort(key=lambda s: s.month)
    return signals


def _issue_month(issue: Any) -> date:
    """DataQualityIssue.record_id is "{project_id}:{YYYY-MM-DD}" for
    per-observation issues (see app/services/ingestion/pipeline.py)."""
    record_id = getattr(issue, "record_id", "")
    _, _, month_str = record_id.rpartition(":")
    try:
        return date.fromisoformat(month_str)
    except ValueError:
        return date.today()
