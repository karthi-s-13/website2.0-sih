from datetime import date

from app.services.anomaly.formulas import (
    EXPENDITURE_ACCELERATION,
    EXPENDITURE_PROGRESS_DIVERGENCE,
    PROGRESS_STAGNATION,
    SCHEDULE_DETERIORATION,
    SUDDEN_PROGRESS_DECLINE,
    detect_anomalies,
    detect_expenditure_acceleration,
    detect_expenditure_progress_divergence,
    detect_progress_stagnation,
    detect_schedule_deterioration,
    detect_sudden_progress_decline,
)
from app.services.features.formulas import ObservationPoint


def _point(month, expenditure, progress, start=date(2024, 1, 1), target=date(2026, 1, 1)):
    return ObservationPoint(
        month=month,
        original_cost_crore=1000.0,
        cumulative_expenditure_crore=expenditure,
        physical_progress_percent=progress,
        start_date=start,
        target_completion_date=target,
    )


def test_no_anomalies_with_insufficient_history() -> None:
    history = [_point(date(2025, 1, 1), 10.0, 5.0), _point(date(2025, 2, 1), 20.0, 10.0)]
    assert detect_anomalies(history) == []


def test_expenditure_acceleration_detected_on_spike() -> None:
    history = [
        _point(date(2025, 1, 1), 10.0, 5.0),
        _point(date(2025, 2, 1), 19.0, 10.0),
        _point(date(2025, 3, 1), 31.0, 15.0),
        _point(date(2025, 4, 1), 40.0, 20.0),
        _point(date(2025, 5, 1), 200.0, 25.0),  # huge jump vs a mildly varying ~+9-12/month baseline
    ]
    anomaly = detect_expenditure_acceleration(history)
    assert anomaly is not None
    assert anomaly.anomaly_type == EXPENDITURE_ACCELERATION
    assert anomaly.severity in {"MODERATE", "HIGH", "CRITICAL"}
    assert 0.0 <= anomaly.score <= 1.0


def test_expenditure_acceleration_not_detected_on_steady_growth() -> None:
    history = [_point(date(2025, i, 1), i * 10.0, i * 5.0) for i in range(1, 7)]
    assert detect_expenditure_acceleration(history) is None


def test_sudden_progress_decline_detected() -> None:
    history = [
        _point(date(2025, 1, 1), 10.0, 5.0),
        _point(date(2025, 2, 1), 20.0, 11.0),
        _point(date(2025, 3, 1), 30.0, 14.0),
        _point(date(2025, 4, 1), 40.0, 20.0),
        _point(date(2025, 5, 1), 50.0, 5.0),  # progress dropped
    ]
    anomaly = detect_sudden_progress_decline(history)
    assert anomaly is not None
    assert anomaly.anomaly_type == SUDDEN_PROGRESS_DECLINE


def test_progress_stagnation_detected_after_three_flat_months() -> None:
    history = [
        _point(date(2025, 1, 1), 10.0, 5.0),
        _point(date(2025, 2, 1), 20.0, 10.0),
        _point(date(2025, 3, 1), 30.0, 10.0),
        _point(date(2025, 4, 1), 40.0, 10.0),
        _point(date(2025, 5, 1), 50.0, 10.0),
    ]
    anomaly = detect_progress_stagnation(history)
    assert anomaly is not None
    assert anomaly.anomaly_type == PROGRESS_STAGNATION
    assert anomaly.severity in {"MODERATE", "HIGH", "CRITICAL"}


def test_progress_stagnation_not_detected_with_only_two_flat_months() -> None:
    history = [
        _point(date(2025, 1, 1), 10.0, 5.0),
        _point(date(2025, 2, 1), 20.0, 10.0),
        _point(date(2025, 3, 1), 30.0, 10.0),
        _point(date(2025, 4, 1), 40.0, 10.0),
    ]
    assert detect_progress_stagnation(history) is None


def test_expenditure_progress_divergence_jump_detected() -> None:
    history = [
        _point(date(2025, 1, 1), 100.0, 10.0),  # util 10%, div 0
        _point(date(2025, 2, 1), 500.0, 12.0),  # util 50%, div 38 -> big jump
    ]
    anomaly = detect_expenditure_progress_divergence(history)
    assert anomaly is not None
    assert anomaly.anomaly_type == EXPENDITURE_PROGRESS_DIVERGENCE


def test_expenditure_progress_divergence_not_detected_when_improving() -> None:
    history = [
        _point(date(2025, 1, 1), 500.0, 10.0),
        _point(date(2025, 2, 1), 520.0, 40.0),  # divergence shrinks
    ]
    assert detect_expenditure_progress_divergence(history) is None


def test_schedule_deterioration_detected() -> None:
    # start 2024-01, target 2026-01 (24 months). Build a gap series that
    # worsens sharply in the final month.
    history = [
        _point(date(2025, 1, 1), 10.0, 40.0),  # elapsed=12/24=50% expected, gap=-10
        _point(date(2025, 2, 1), 20.0, 41.0),  # elapsed=13/24=54.2%, gap=-13.2
        _point(date(2025, 3, 1), 30.0, 42.0),  # elapsed=14/24=58.3%, gap=-16.3
        _point(date(2025, 4, 1), 40.0, 10.0),  # elapsed=15/24=62.5%, gap=-52.5 (sharp drop)
    ]
    anomaly = detect_schedule_deterioration(history)
    assert anomaly is not None
    assert anomaly.anomaly_type == SCHEDULE_DETERIORATION


def test_detect_anomalies_returns_list_not_dict() -> None:
    history = [_point(date(2025, i, 1), i * 10.0, i * 5.0) for i in range(1, 7)]
    result = detect_anomalies(history)
    assert isinstance(result, list)


def test_detect_anomalies_empty_history() -> None:
    assert detect_anomalies([]) == []
