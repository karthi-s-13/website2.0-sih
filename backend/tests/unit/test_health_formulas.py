from datetime import date

import pytest

from app.services.features.formulas import ObservationPoint
from app.services.health.formulas import (
    MilestoneHealth,
    compute_health,
    compute_milestone_health,
)


def add_months(d: date, n: int) -> date:
    total = d.year * 12 + (d.month - 1) + n
    return date(total // 12, total % 12 + 1, 1)


NO_MILESTONES = MilestoneHealth(status="NOT_AVAILABLE", total=0, completed=0, delayed=0)


def make_point(month: date, **overrides) -> ObservationPoint:
    defaults = dict(
        month=month,
        original_cost_crore=500.0,
        cumulative_expenditure_crore=342.0,
        physical_progress_percent=52.1,
        start_date=date(2000, 1, 1),
        target_completion_date=add_months(date(2000, 1, 1), 500),
    )
    defaults.update(overrides)
    return ObservationPoint(**defaults)


def test_matches_spec_example_exactly() -> None:
    """Reproduces the Phase 4 spec's own example output:
    cost_utilisation=68.4, schedule_utilisation=74.2, physical_progress=52.1,
    expected_progress=74.2, progress_gap=-22.1,
    expenditure_progress_divergence=16.3, overall_health="WATCH".
    """
    start = date(2000, 1, 1)
    snapshot = add_months(start, 371)  # elapsed=371, planned=500 -> 74.2%
    point = make_point(snapshot, start_date=start, target_completion_date=add_months(start, 500))

    vector = compute_health([point], snapshot, NO_MILESTONES)

    assert vector.cost_utilisation == pytest.approx(68.4)
    assert vector.schedule_utilisation == pytest.approx(74.2)
    assert vector.physical_progress == pytest.approx(52.1)
    assert vector.expected_progress == pytest.approx(74.2)
    assert vector.progress_gap == pytest.approx(-22.1)
    assert vector.expenditure_progress_divergence == pytest.approx(16.3)
    assert vector.overall_health == "WATCH"


def test_no_history_raises() -> None:
    with pytest.raises(ValueError):
        compute_health([], date(2025, 1, 1), NO_MILESTONES)


def test_missing_start_date_yields_null_schedule_fields() -> None:
    point = make_point(date(2025, 1, 1), start_date=None)
    vector = compute_health([point], date(2025, 1, 1), NO_MILESTONES)
    assert vector.schedule_utilisation is None
    assert vector.expected_progress is None
    assert vector.progress_gap is None
    # cost-side fields still computed
    assert vector.cost_utilisation == pytest.approx(68.4)
    assert vector.expenditure_progress_divergence == pytest.approx(68.4 - 52.1)


def test_overall_health_data_not_available_when_nothing_computable() -> None:
    point = make_point(
        date(2025, 1, 1), start_date=None, original_cost_crore=None, physical_progress_percent=None
    )
    vector = compute_health([point], date(2025, 1, 1), NO_MILESTONES)
    assert vector.overall_health == "DATA_NOT_AVAILABLE"


@pytest.mark.parametrize(
    "progress_gap_shortfall,divergence,expected",
    [
        (0, 0, "NORMAL"),
        (20, 0, "WATCH"),
        (0, 12, "WATCH"),
        (35, 0, "ELEVATED"),
        (0, 45, "HIGH"),
        (80, 0, "CRITICAL"),
        (10, 30, "ELEVATED"),  # overall = worse of the two tiers
    ],
)
def test_overall_health_tiers(progress_gap_shortfall: float, divergence: float, expected: str) -> None:
    start = date(2020, 1, 1)
    planned = 100
    snapshot = add_months(start, planned)
    # physical_progress chosen so progress_gap == -progress_gap_shortfall
    expected_progress = 100.0  # elapsed == planned == 100 -> schedule_utilisation 100%
    physical_progress = expected_progress - progress_gap_shortfall
    cost_utilisation = physical_progress + divergence

    point = ObservationPoint(
        month=snapshot,
        original_cost_crore=1000.0,
        cumulative_expenditure_crore=cost_utilisation * 10,  # /1000 -> cost_utilisation%
        physical_progress_percent=physical_progress,
        start_date=start,
        target_completion_date=add_months(start, planned),
    )
    vector = compute_health([point], snapshot, NO_MILESTONES)
    assert vector.overall_health == expected


def test_recent_trend_stagnant_bumps_overall_health() -> None:
    start = date(2020, 1, 1)
    target = add_months(start, 100)
    months = [add_months(start, i) for i in range(5)]
    # physical_progress flat for the last 3+ months -> STAGNANT
    points = [
        ObservationPoint(
            month=m,
            original_cost_crore=1000.0,
            cumulative_expenditure_crore=100.0,
            physical_progress_percent=10.0,
            start_date=start,
            target_completion_date=target,
        )
        for m in months
    ]
    vector = compute_health(points, months[-1], NO_MILESTONES)
    assert vector.recent_trend.label == "STAGNANT"
    assert vector.recent_trend.consecutive_stagnant_months >= 3
    # without the stagnation bump this would be NORMAL (on schedule, no divergence)
    assert vector.overall_health == "WATCH"


def test_recent_trend_improving_and_declining() -> None:
    start = date(2020, 1, 1)
    target = add_months(start, 100)

    def build(progress_values: list[float]):
        months = [add_months(start, i) for i in range(len(progress_values))]
        points = [
            ObservationPoint(
                month=m,
                original_cost_crore=1000.0,
                cumulative_expenditure_crore=100.0,
                physical_progress_percent=p,
                start_date=start,
                target_completion_date=target,
            )
            for m, p in zip(months, progress_values, strict=True)
        ]
        return compute_health(points, months[-1], NO_MILESTONES)

    improving = build([10.0, 20.0, 30.0])
    declining = build([30.0, 20.0, 10.0])
    assert improving.recent_trend.label == "IMPROVING"
    assert declining.recent_trend.label == "DECLINING"


def test_compute_milestone_health_empty() -> None:
    result = compute_milestone_health([])
    assert result.status == "NOT_AVAILABLE"
    assert result.total == 0


class _FakeMilestone:
    def __init__(self, status=None, planned_date=None, actual_date=None):
        self.status = status
        self.planned_date = planned_date
        self.actual_date = actual_date


def test_compute_milestone_health_all_on_time() -> None:
    milestones = [
        _FakeMilestone("COMPLETED", date(2024, 1, 1), date(2024, 1, 1)),
        _FakeMilestone("COMPLETED", date(2024, 2, 1), date(2024, 1, 15)),
    ]
    result = compute_milestone_health(milestones)
    assert result.status == "GOOD"
    assert result.total == 2
    assert result.completed == 2
    assert result.delayed == 0


def test_compute_milestone_health_delayed() -> None:
    milestones = [
        _FakeMilestone("COMPLETED", date(2024, 1, 1), date(2024, 2, 1)),  # delayed
        _FakeMilestone("PENDING", date(2024, 2, 1), None),
    ]
    result = compute_milestone_health(milestones)
    assert result.delayed == 1
    assert result.status in {"WATCH", "POOR"}
