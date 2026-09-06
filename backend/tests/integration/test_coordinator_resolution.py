from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.services.coordinator.resolution import AMBIGUOUS, NOT_FOUND, RESOLVED, resolve_project
from app.services.ingestion.pipeline import ingest_directory

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"


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


def test_explicit_project_id_short_circuits(ingested_session: Session) -> None:
    result = resolve_project(ingested_session, "irrelevant query text", explicit_project_id="617069")
    assert result.status == RESOLVED
    assert result.project_id == "617069"


def test_explicit_project_id_not_found(ingested_session: Session) -> None:
    result = resolve_project(ingested_session, "irrelevant", explicit_project_id="does-not-exist")
    assert result.status == NOT_FOUND


def test_exact_project_id_in_query_resolves(ingested_session: Session) -> None:
    result = resolve_project(ingested_session, "619054")
    assert result.status == RESOLVED
    assert result.project_id == "619054"


def test_full_project_name_resolves(ingested_session: Session) -> None:
    result = resolve_project(ingested_session, "Development of Keshod Airport.")
    assert result.status == RESOLVED
    assert result.project_id == "619054"


def test_distinctive_partial_name_resolves(ingested_session: Session) -> None:
    result = resolve_project(ingested_session, "What is the cost risk for Keshod Airport?")
    assert result.status == RESOLVED
    assert result.project_id == "619054"


def test_unrelated_query_not_found(ingested_session: Session) -> None:
    result = resolve_project(ingested_session, "What is the weather today?")
    assert result.status == NOT_FOUND


def test_generic_query_does_not_false_positive_match(ingested_session: Session) -> None:
    # A generic query sharing only common infrastructure words with many
    # project names must not resolve to anything (avoids the "one token
    # overlap = match" false-positive trap).
    result = resolve_project(ingested_session, "What is the cost risk for this power project?")
    assert result.status == NOT_FOUND
