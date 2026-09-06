from datetime import date

import pytest

from app.services.features.formulas import ObservationPoint, compute_feature_vector, months_between


def test_months_between() -> None:
    assert months_between(date(2025, 2, 1), date(2025, 8, 1)) == 6
    assert months_between(date(2025, 2, 1), date(2027, 2, 1)) == 24
    assert months_between(date(2025, 8, 1), date(2025, 2, 1)) == -6


def test_compute_feature_vector_requires_history() -> None:
    with pytest.raises(ValueError):
        compute_feature_vector([], date(2025, 1, 1))


def test_first_observation_only_partial_features() -> None:
    # KPS1 project, 2025-07: no start_date known yet (real data: blank until the
    # second report), so anything schedule-dependent must be None, not fabricated.
    obs1 = ObservationPoint(
        month=date(2025, 7, 1),
        original_cost_crore=466.00,
        cumulative_expenditure_crore=6.99,
        physical_progress_percent=0.00,
        start_date=None,
        target_completion_date=date(2027, 2, 1),
    )
    vector = compute_feature_vector([obs1], snapshot_month=date(2025, 7, 1))

    assert vector.cost_utilisation == pytest.approx(0.015)
    assert vector.schedule_utilisation is None
    assert vector.expected_progress is None
    assert vector.progress_gap is None
    assert vector.expenditure_progress_divergence == pytest.approx(0.015)
    assert vector.monthly_progress_change is None
    assert vector.monthly_expenditure_growth is None
    assert vector.expenditure_growth is None
    assert vector.rolling_progress_change is None
    assert vector.rolling_expenditure_change is None
    assert vector.project_age_months is None
    assert vector.remaining_schedule_months is None
    assert vector.remaining_cost_budget_crore == pytest.approx(459.01)
    assert vector.input_observation_count == 1


def test_second_observation_full_features() -> None:
    # KPS1 project, 2025-08: matches the real second Flash Report row exactly
    # (hand-computed expected values, independent of the implementation).
    obs1 = ObservationPoint(
        month=date(2025, 7, 1),
        original_cost_crore=466.00,
        cumulative_expenditure_crore=6.99,
        physical_progress_percent=0.00,
        start_date=None,
        target_completion_date=date(2027, 2, 1),
    )
    obs2 = ObservationPoint(
        month=date(2025, 8, 1),
        original_cost_crore=466.00,
        cumulative_expenditure_crore=13.99,
        physical_progress_percent=1.00,
        start_date=date(2025, 2, 1),
        target_completion_date=date(2027, 2, 1),
    )
    vector = compute_feature_vector([obs1, obs2], snapshot_month=date(2025, 8, 1))

    assert vector.cost_utilisation == pytest.approx(13.99 / 466.00)
    assert vector.schedule_utilisation == pytest.approx(0.25)
    assert vector.physical_progress == pytest.approx(1.00)
    assert vector.expected_progress == pytest.approx(25.0)
    assert vector.progress_gap == pytest.approx(-24.0)
    assert vector.expenditure_progress_divergence == pytest.approx((13.99 / 466.00) - 0.01)
    assert vector.monthly_progress_change == pytest.approx(1.00)
    assert vector.monthly_expenditure_growth == pytest.approx(7.00)
    assert vector.expenditure_growth == pytest.approx(7.00 / 6.99)
    assert vector.rolling_progress_change == pytest.approx(1.00)
    assert vector.rolling_expenditure_change == pytest.approx(7.00)
    assert vector.project_age_months == 6
    assert vector.remaining_schedule_months == 18
    assert vector.remaining_cost_budget_crore == pytest.approx(452.01)
    assert vector.input_observation_count == 2


def test_rolling_window_uses_only_trailing_n_deltas() -> None:
    base = dict(
        original_cost_crore=100.0, start_date=date(2025, 1, 1), target_completion_date=date(2026, 1, 1)
    )
    obs = [
        ObservationPoint(
            month=date(2025, m, 1),
            cumulative_expenditure_crore=float(m),
            physical_progress_percent=float(m),
            **base,
        )
        for m in range(1, 6)  # cum expenditure/progress: 1,2,3,4,5 -> deltas all 1.0
    ]
    vector = compute_feature_vector(obs, snapshot_month=date(2025, 5, 1), rolling_window_months=3)
    # 4 deltas available (1,1,1,1); only the trailing 3 are averaged.
    assert vector.rolling_expenditure_change == pytest.approx(1.0)
    assert vector.rolling_progress_change == pytest.approx(1.0)


def test_division_guards_return_none_not_error() -> None:
    obs = ObservationPoint(
        month=date(2025, 1, 1),
        original_cost_crore=0.0,
        cumulative_expenditure_crore=5.0,
        physical_progress_percent=10.0,
        start_date=date(2025, 1, 1),
        target_completion_date=date(2025, 1, 1),  # zero-length duration
    )
    vector = compute_feature_vector([obs], snapshot_month=date(2025, 1, 1))
    assert vector.cost_utilisation is None  # original_cost_crore <= 0
    assert vector.schedule_utilisation is None  # original_duration_months == 0
