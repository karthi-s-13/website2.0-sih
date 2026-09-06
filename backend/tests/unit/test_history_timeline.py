from datetime import date
from types import SimpleNamespace

from app.services.history.timeline import (
    INFERRED_TREND,
    MODEL_PREDICTION,
    OBSERVED_FACT,
    build_major_changes,
    build_risk_signals,
    build_timeline,
)


def obs(month, cum_exp=10.0, progress=5.0, notes=None):
    return SimpleNamespace(
        observation_month=month, cumulative_expenditure_crore=cum_exp, physical_progress_percent=progress, notes=notes
    )


def event(month, event_type, description="something changed", previous_value=None, new_value=None):
    return SimpleNamespace(
        event_month=month,
        event_type=event_type,
        description=description,
        previous_value=previous_value,
        new_value=new_value,
    )


def dq_issue(record_id, issue_type, field="physical_progress_percent", original_value="1.0", severity="WARNING"):
    return SimpleNamespace(
        record_id=record_id,
        issue_type=issue_type,
        field=field,
        original_value=original_value,
        severity=severity,
    )


def test_build_timeline_all_observations_are_observed_fact() -> None:
    observations = [obs(date(2025, 1, 1)), obs(date(2025, 2, 1))]
    timeline = build_timeline(observations, [])
    assert len(timeline) == 2
    assert all(e.source_type == OBSERVED_FACT for e in timeline)
    assert [e.month for e in timeline] == [date(2025, 1, 1), date(2025, 2, 1)]


def test_build_timeline_is_chronologically_sorted_with_events_interleaved() -> None:
    observations = [obs(date(2025, 1, 1)), obs(date(2025, 3, 1))]
    events = [event(date(2025, 2, 1), "COST_REVISED")]
    timeline = build_timeline(observations, events)
    assert [e.month for e in timeline] == [date(2025, 1, 1), date(2025, 2, 1), date(2025, 3, 1)]
    assert timeline[1].source_type == OBSERVED_FACT
    assert timeline[1].title == "Cost Revised"


def test_build_timeline_includes_notes() -> None:
    timeline = build_timeline([obs(date(2025, 1, 1), notes="land acquisition delay")], [])
    assert "land acquisition delay" in timeline[0].description


def test_build_major_changes_excludes_first_observed() -> None:
    events = [
        event(date(2025, 1, 1), "PROJECT_FIRST_OBSERVED"),
        event(date(2025, 2, 1), "COST_REVISED", previous_value="100", new_value="120"),
    ]
    changes = build_major_changes(events)
    assert len(changes) == 1
    assert changes[0].change_type == "COST_REVISED"
    assert changes[0].source_type == OBSERVED_FACT
    assert changes[0].previous_value == "100"
    assert changes[0].new_value == "120"


def test_build_risk_signals_dq_issues_are_inferred_trend() -> None:
    issues = [dq_issue("617069:2025-11-01", "NON_MONOTONIC_PHYSICAL_PROGRESS")]
    signals = build_risk_signals(
        dq_issues=issues,
        health_snapshot_month=date(2025, 12, 1),
        overall_health="NORMAL",
        progress_gap=0.0,
        expenditure_progress_divergence=0.0,
        ml_probability=None,
        ml_risk_level=None,
        ml_model_version=None,
    )
    assert len(signals) == 1
    assert signals[0].source_type == INFERRED_TREND
    assert signals[0].month == date(2025, 11, 1)


def test_build_risk_signals_ignores_non_risk_dq_issue_types() -> None:
    issues = [dq_issue("617069:2025-11-01", "MISSING_REQUIRED_FIELD")]
    signals = build_risk_signals(
        dq_issues=issues,
        health_snapshot_month=date(2025, 12, 1),
        overall_health="NORMAL",
        progress_gap=0.0,
        expenditure_progress_divergence=0.0,
        ml_probability=None,
        ml_risk_level=None,
        ml_model_version=None,
    )
    assert signals == []


def test_build_risk_signals_concerning_health_adds_inferred_trend_entry() -> None:
    signals = build_risk_signals(
        dq_issues=[],
        health_snapshot_month=date(2025, 12, 1),
        overall_health="ELEVATED",
        progress_gap=-33.8,
        expenditure_progress_divergence=-3.8,
        ml_probability=None,
        ml_risk_level=None,
        ml_model_version=None,
    )
    assert len(signals) == 1
    assert signals[0].source_type == INFERRED_TREND
    assert signals[0].signal_type == "HEALTH_TIER"
    assert "behind expected schedule" in signals[0].description


def test_build_risk_signals_normal_health_adds_nothing() -> None:
    signals = build_risk_signals(
        dq_issues=[],
        health_snapshot_month=date(2025, 12, 1),
        overall_health="NORMAL",
        progress_gap=1.0,
        expenditure_progress_divergence=0.0,
        ml_probability=None,
        ml_risk_level=None,
        ml_model_version=None,
    )
    assert signals == []


def test_build_risk_signals_ml_prediction_is_model_prediction() -> None:
    signals = build_risk_signals(
        dq_issues=[],
        health_snapshot_month=date(2025, 12, 1),
        overall_health="NORMAL",
        progress_gap=1.0,
        expenditure_progress_divergence=0.0,
        ml_probability=0.13,
        ml_risk_level="LOW",
        ml_model_version="cost-overrun-lightgbm-test",
    )
    assert len(signals) == 1
    assert signals[0].source_type == MODEL_PREDICTION
    assert "13.0%" in signals[0].description
    assert "not a confirmed outcome" in signals[0].description


def test_build_risk_signals_sorted_chronologically() -> None:
    issues = [
        dq_issue("617069:2025-11-01", "NON_MONOTONIC_PHYSICAL_PROGRESS"),
        dq_issue("617069:2025-06-01", "NON_MONOTONIC_CUMULATIVE_EXPENDITURE"),
    ]
    signals = build_risk_signals(
        dq_issues=issues,
        health_snapshot_month=date(2025, 12, 1),
        overall_health="NORMAL",
        progress_gap=0.0,
        expenditure_progress_divergence=0.0,
        ml_probability=None,
        ml_risk_level=None,
        ml_model_version=None,
    )
    assert [s.month for s in signals] == [date(2025, 6, 1), date(2025, 11, 1)]
