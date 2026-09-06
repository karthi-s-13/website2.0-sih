from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.core.errors import NotFoundError
from app.services.anomaly.formulas import UNEXPECTED_MILESTONE_CHANGES
from app.services.anomaly.service import get_project_anomalies
from app.services.ingestion.pipeline import ingest_directory

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
VALID_PROJECT_IDS = ["617069", "619054", "616672", "617184", "617279"]


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


def test_anomalies_for_all_five_projects_do_not_error(ingested_session: Session) -> None:
    for project_id in VALID_PROJECT_IDS:
        result = get_project_anomalies(ingested_session, project_id, as_of_date=date(2026, 12, 1))
        assert result.project_id == project_id
        for a in result.anomalies:
            assert a.severity in {"MODERATE", "HIGH", "CRITICAL"}
            assert 0.0 <= a.score <= 1.0


def test_milestones_reported_unavailable(ingested_session: Session) -> None:
    result = get_project_anomalies(
        ingested_session, "617069", as_of_date=date(2026, 12, 1)
    )
    assert result.unavailable_types == [UNEXPECTED_MILESTONE_CHANGES]


def test_project_not_found_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        get_project_anomalies(session, "does-not-exist", as_of_date=date(2026, 1, 1))
