from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.core.errors import DataQualityFailureError, NotFoundError
from app.models.project import Project
from app.services.health.formulas import HEALTH_LEVELS
from app.services.health.service import get_project_health
from app.services.ingestion.pipeline import ingest_directory

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
VALID_PROJECT_IDS = ["617069", "619054", "616672", "617184", "617279"]
VALID_OVERALL_HEALTH = {*HEALTH_LEVELS, "DATA_NOT_AVAILABLE"}


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


def test_dashboard_can_display_health_for_all_five_projects(ingested_session: Session) -> None:
    """Exit criterion: the dashboard can display health metrics for all five projects."""
    for project_id in VALID_PROJECT_IDS:
        project = ingested_session.get(Project, project_id)
        vector = get_project_health(ingested_session, project_id, project.latest_observation_month)

        assert vector.overall_health in VALID_OVERALL_HEALTH
        assert vector.milestone_health.status == "NOT_AVAILABLE"  # no real milestone data (Phase 1)
        if vector.cost_utilisation is not None:
            assert vector.cost_utilisation >= 0
        if vector.physical_progress is not None:
            assert 0 <= vector.physical_progress <= 100


def test_health_is_deterministic(ingested_session: Session) -> None:
    project = ingested_session.get(Project, "617069")
    first = get_project_health(ingested_session, "617069", project.latest_observation_month)
    second = get_project_health(ingested_session, "617069", project.latest_observation_month)
    assert first.overall_health == second.overall_health
    assert first.cost_utilisation == second.cost_utilisation
    assert first.progress_gap == second.progress_gap


def test_unknown_project_raises_not_found(ingested_session: Session) -> None:
    from datetime import date

    with pytest.raises(NotFoundError):
        get_project_health(ingested_session, "does-not-exist", date(2025, 1, 1))


def test_health_before_any_observation_raises_data_quality_failure(ingested_session: Session) -> None:
    from datetime import date

    project = ingested_session.get(Project, "617069")
    before_first = date(project.first_observation_month.year - 1, 1, 1)
    with pytest.raises(DataQualityFailureError):
        get_project_health(ingested_session, "617069", before_first)


def test_kps1_health_uses_only_point_in_time_data(ingested_session: Session) -> None:
    """A health check for the FIRST observed month must not see later months."""
    project = ingested_session.get(Project, "617069")
    vector = get_project_health(ingested_session, "617069", project.first_observation_month)
    assert vector.input_observation_count == 1
    # first row: start_date not yet known in the real data -> schedule fields null
    assert vector.schedule_utilisation is None
