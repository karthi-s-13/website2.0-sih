from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.core.errors import DataLeakageError
from app.repositories.feature_repository import get_feature_history
from app.services.features.pipeline import (
    FEATURE_VERSION,
    build_features,
    filter_point_in_time,
    validate_point_in_time,
)
from app.services.ingestion.pipeline import ingest_directory

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"

EXPECTED_OBSERVATION_COUNTS = {
    "617069": 13,
    "619054": 7,
    "616672": 19,
    "617184": 17,
    "617279": 14,
}


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def ingested_session(session: Session) -> Session:
    ingest_directory(session, RAW_DIR)
    return session


def test_validate_point_in_time_raises_on_future_data() -> None:
    future = SimpleNamespace(observation_month=date(2026, 12, 1))
    with pytest.raises(DataLeakageError):
        validate_point_in_time([future], snapshot_month=date(2026, 1, 1))


def test_validate_point_in_time_allows_past_and_present() -> None:
    past = SimpleNamespace(observation_month=date(2025, 1, 1))
    present = SimpleNamespace(observation_month=date(2025, 6, 1))
    validate_point_in_time([past, present], snapshot_month=date(2025, 6, 1))  # must not raise


def test_filter_point_in_time_excludes_future_rows() -> None:
    rows = [
        SimpleNamespace(observation_month=date(2025, 1, 1)),
        SimpleNamespace(observation_month=date(2025, 2, 1)),
        SimpleNamespace(observation_month=date(2025, 3, 1)),
    ]
    filtered = filter_point_in_time(rows, snapshot_month=date(2025, 2, 1))
    assert [r.observation_month for r in filtered] == [date(2025, 1, 1), date(2025, 2, 1)]


def test_one_feature_row_per_observed_month(ingested_session: Session) -> None:
    build_features(ingested_session)
    for project_id, expected_count in EXPECTED_OBSERVATION_COUNTS.items():
        rows = get_feature_history(ingested_session, project_id, FEATURE_VERSION)
        assert len(rows) == expected_count


def test_every_feature_row_satisfies_point_in_time_invariant(ingested_session: Session) -> None:
    """assert max(feature_timestamp) <= prediction_timestamp for every row."""
    from app.models.project import ProjectMonthlyObservation

    build_features(ingested_session)
    for project_id in EXPECTED_OBSERVATION_COUNTS:
        observations = (
            ingested_session.query(ProjectMonthlyObservation)
            .filter_by(project_id=project_id)
            .order_by(ProjectMonthlyObservation.observation_month)
            .all()
        )
        feature_rows = get_feature_history(ingested_session, project_id, FEATURE_VERSION)
        for feature_row in feature_rows:
            inputs_used = [o for o in observations if o.observation_month <= feature_row.snapshot_month]
            max_feature_timestamp = max(o.observation_month for o in inputs_used)
            assert max_feature_timestamp <= feature_row.snapshot_month
            # input_observation_count must match what point-in-time filtering allows -
            # never more (that would mean future data leaked in).
            assert feature_row.input_observation_count == len(inputs_used)


def test_features_are_deterministic_across_rebuilds(ingested_session: Session) -> None:
    """Exit criterion: the same project/month produces the same features every time."""
    build_features(ingested_session)
    first_pass = {
        (row.project_id, row.snapshot_month): _snapshot(row)
        for project_id in EXPECTED_OBSERVATION_COUNTS
        for row in get_feature_history(ingested_session, project_id, FEATURE_VERSION)
    }

    build_features(ingested_session)  # rebuild in place
    second_pass = {
        (row.project_id, row.snapshot_month): _snapshot(row)
        for project_id in EXPECTED_OBSERVATION_COUNTS
        for row in get_feature_history(ingested_session, project_id, FEATURE_VERSION)
    }

    assert first_pass == second_pass
    assert len(first_pass) == sum(EXPECTED_OBSERVATION_COUNTS.values())


def test_kps1_first_two_months_match_hand_computed_values(ingested_session: Session) -> None:
    build_features(ingested_session)
    rows = {row.snapshot_month: row for row in get_feature_history(ingested_session, "617069", FEATURE_VERSION)}

    first = rows[date(2025, 7, 1)]
    assert first.cost_utilisation == pytest.approx(0.015)
    assert first.schedule_utilisation is None
    assert first.remaining_cost_budget_crore == pytest.approx(459.01)

    second = rows[date(2025, 8, 1)]
    assert second.schedule_utilisation == pytest.approx(0.25)
    assert second.progress_gap == pytest.approx(-24.0)
    assert second.monthly_expenditure_growth == pytest.approx(7.00)
    assert second.project_age_months == 6


def _snapshot(row) -> tuple:
    return (
        row.cost_utilisation,
        row.expenditure_growth,
        row.monthly_expenditure_growth,
        row.schedule_utilisation,
        row.physical_progress,
        row.expected_progress,
        row.progress_gap,
        row.expenditure_progress_divergence,
        row.monthly_progress_change,
        row.rolling_progress_change,
        row.rolling_expenditure_change,
        row.project_age_months,
        row.remaining_schedule_months,
        row.remaining_cost_budget_crore,
        row.input_observation_count,
    )
