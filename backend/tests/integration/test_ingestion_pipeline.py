from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.repositories.project_repository import (
    get_chronological_observations,
    get_project,
    get_project_events,
)
from app.services.ingestion.pipeline import ingest_directory
from app.services.validation_cohort import INITIAL_VALIDATION_COHORT, seed_validation_cohort

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"

EXPECTED_OBSERVATION_COUNTS = {
    "617069": 13,  # KPS1
    "619054": 7,  # Keshod Airport
    "616672": 19,  # Koppal-Gadag
    "617184": 17,  # Davanagere/Chitradurga/Bellary REZ
    "617279": 14,  # Mahan Energen
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
    seed_validation_cohort(session)
    return session


def test_raw_dir_has_the_five_validation_files() -> None:
    assert RAW_DIR.is_dir()
    assert len(list(RAW_DIR.glob("*.csv"))) == 5


def test_all_five_validation_projects_are_retrievable(ingested_session: Session) -> None:
    for project_id in EXPECTED_OBSERVATION_COUNTS:
        project = get_project(ingested_session, project_id)
        assert project is not None, f"project {project_id} was not ingested"


def test_observations_are_complete_and_chronological(ingested_session: Session) -> None:
    for project_id, expected_count in EXPECTED_OBSERVATION_COUNTS.items():
        observations = get_chronological_observations(ingested_session, project_id)
        assert len(observations) == expected_count, (
            f"{project_id}: expected {expected_count} observations, got {len(observations)}"
        )
        months = [o.observation_month for o in observations]
        assert months == sorted(months), f"{project_id}: observations are not chronological"
        assert len(months) == len(set(months)), f"{project_id}: duplicate observation months present"


def test_no_observations_were_silently_dropped(ingested_session: Session) -> None:
    from app.services.ingestion.pipeline import ingest_directory as _ingest

    summary = _ingest(ingested_session, RAW_DIR)
    assert summary.observations_quarantined == 0


def test_project_master_fields_populated(ingested_session: Session) -> None:
    project = get_project(ingested_session, "617069")
    assert project.project_name.startswith("Augmentation of Transformation Capacity")
    assert project.agency_code == "POWERGRID"
    assert project.state == "Gujarat"
    assert project.original_cost_crore == 466.0
    assert project.first_observation_month.isoformat() == "2025-07-01"
    assert project.latest_observation_month.isoformat() == "2026-07-01"
    assert project.observation_count == 13


def test_keshod_first_observation_has_no_progress_yet(ingested_session: Session) -> None:
    observations = get_chronological_observations(ingested_session, "619054")
    first = observations[0]
    assert first.cumulative_expenditure_crore is None
    assert first.physical_progress_percent is None
    assert first.record_type == "Newly Added Projects"


def test_project_first_observed_event_recorded(ingested_session: Session) -> None:
    events = get_project_events(ingested_session, "617069")
    assert events[0].event_type == "PROJECT_FIRST_OBSERVED"


def test_non_monotonic_progress_is_flagged_not_dropped(ingested_session: Session) -> None:
    # KPS1 physical progress drops from 2.00 (2025-10) to 1.00 (2025-11).
    from app.models.data_quality import DataQualityIssue

    issues = (
        ingested_session.query(DataQualityIssue)
        .filter(DataQualityIssue.issue_type == "NON_MONOTONIC_PHYSICAL_PROGRESS")
        .all()
    )
    assert len(issues) > 0
    observations = get_chronological_observations(ingested_session, "617069")
    by_month = {o.observation_month.isoformat(): o for o in observations}
    assert by_month["2025-11-01"].physical_progress_percent == 1.0  # kept as observed


def test_validation_cohort_seeded(ingested_session: Session) -> None:
    from app.models.validation_cohort import ValidationCohort

    rows = ingested_session.query(ValidationCohort).all()
    assert {row.project_id for row in rows} == set(INITIAL_VALIDATION_COHORT.keys())


def test_ingestion_is_idempotent(session: Session) -> None:
    first = ingest_directory(session, RAW_DIR)
    second = ingest_directory(session, RAW_DIR)
    assert first.observations_upserted == second.observations_upserted
    assert second.raw_rows_newly_stored == 0
    total_observations = sum(EXPECTED_OBSERVATION_COUNTS.values())
    assert first.observations_upserted == total_observations


def test_rerunning_ingestion_does_not_duplicate_quality_issues(session: Session) -> None:
    from app.models.data_quality import DataQualityIssue

    ingest_directory(session, RAW_DIR)
    count_after_first = session.query(DataQualityIssue).count()
    ingest_directory(session, RAW_DIR)
    count_after_second = session.query(DataQualityIssue).count()
    assert count_after_first > 0
    assert count_after_second == count_after_first
