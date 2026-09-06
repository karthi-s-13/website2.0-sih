from datetime import date

from app.services.ingestion.quality import (
    check_monotonic_sequences,
    deduplicate_project_month,
    validate_ranges,
)
from app.services.ingestion.schema import NormalizedObservation


def make_obs(**overrides) -> NormalizedObservation:
    defaults = dict(
        source_file="test.csv",
        source_row=1,
        raw_row={},
        project_id="P1",
        observation_month=date(2025, 1, 1),
        original_cost_crore=100.0,
        cumulative_expenditure_crore=10.0,
        physical_progress_percent=5.0,
    )
    defaults.update(overrides)
    return NormalizedObservation(**defaults)


def test_validate_ranges_flags_progress_out_of_bounds() -> None:
    obs = make_obs(physical_progress_percent=150.0)
    issues = validate_ranges(obs)
    assert any(i.issue_type == "INVALID_RANGE" and i.field == "physical_progress_percent" for i in issues)


def test_validate_ranges_flags_negative_expenditure() -> None:
    obs = make_obs(cumulative_expenditure_crore=-5.0)
    issues = validate_ranges(obs)
    assert any(i.field == "cumulative_expenditure_crore" for i in issues)


def test_validate_ranges_flags_non_positive_original_cost() -> None:
    obs = make_obs(original_cost_crore=0.0)
    issues = validate_ranges(obs)
    assert any(i.field == "original_cost_crore" for i in issues)


def test_validate_ranges_clean_row_has_no_issues() -> None:
    obs = make_obs()
    assert validate_ranges(obs) == []


def test_deduplicate_keeps_more_complete_row() -> None:
    sparse = make_obs(source_row=1, cumulative_expenditure_crore=None, physical_progress_percent=None)
    complete = make_obs(source_row=2, cumulative_expenditure_crore=10.0, physical_progress_percent=5.0)
    kept, dropped = deduplicate_project_month([sparse, complete])
    assert len(kept) == 1
    assert kept[0].source_row == 2
    assert len(dropped) == 1
    assert dropped[0][1].issue_type == "DUPLICATE_PROJECT_MONTH"


def test_deduplicate_no_duplicates_keeps_all() -> None:
    a = make_obs(observation_month=date(2025, 1, 1))
    b = make_obs(observation_month=date(2025, 2, 1))
    kept, dropped = deduplicate_project_month([a, b])
    assert len(kept) == 2
    assert dropped == []


def test_monotonic_check_flags_decrease() -> None:
    jan = make_obs(observation_month=date(2025, 1, 1), physical_progress_percent=10.0)
    feb = make_obs(observation_month=date(2025, 2, 1), physical_progress_percent=5.0)
    issues = check_monotonic_sequences([jan, feb])
    assert any(i.issue_type == "NON_MONOTONIC_PHYSICAL_PROGRESS" for _, i in issues)


def test_monotonic_check_allows_increase_or_flat() -> None:
    jan = make_obs(observation_month=date(2025, 1, 1), cumulative_expenditure_crore=10.0)
    feb = make_obs(observation_month=date(2025, 2, 1), cumulative_expenditure_crore=10.0)
    mar = make_obs(observation_month=date(2025, 3, 1), cumulative_expenditure_crore=15.0)
    issues = check_monotonic_sequences([jan, feb, mar])
    assert issues == []
