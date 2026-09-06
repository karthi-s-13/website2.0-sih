from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.core.errors import NotFoundError
from app.repositories.web_evidence_repository import get_evidence_for_project
from app.services.ingestion.pipeline import ingest_directory
from app.services.web.claim_extraction import ExtractedClaim
from app.services.web.search_client import SearchResult, WebSearchUnavailableError
from app.services.web.service import get_web_intelligence

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
PROJECT_ID = "617069"  # ELEVATED health per Phase 5 portfolio summary - not HIGH/CRITICAL

FAKE_RESULTS = [
    SearchResult(
        title="Bihar bridge project delayed by dispute",
        url="https://www.thehindu.com/news/bridge-delay",
        content="The project has faced a contractor dispute.",
        published_date_raw="2025-08-14",
    )
]


def _fake_claims(results, *args, **kwargs):
    return [ExtractedClaim(result=r, finding="A contractor dispute was reported.", project_relevance=0.8) for r in results]


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


def test_not_triggered_when_risk_is_not_high(ingested_session: Session) -> None:
    with patch("app.services.web.service.search_web") as mock_search:
        result = get_web_intelligence(ingested_session, PROJECT_ID)

    assert result.triggered is False
    assert result.evidence == []
    mock_search.assert_not_called()


def test_triggered_by_force_runs_pipeline_and_stores_evidence(ingested_session: Session) -> None:
    with (
        patch("app.services.web.service.search_web", return_value=FAKE_RESULTS),
        patch("app.services.web.service.extract_claims", side_effect=lambda results, **kw: _fake_claims(results)),
    ):
        result = get_web_intelligence(ingested_session, PROJECT_ID, force=True)

    assert result.triggered is True
    assert "force" in result.trigger_reason.lower()
    assert len(result.evidence) > 0
    item = result.evidence[0]
    assert item.url == "https://www.thehindu.com/news/bridge-delay"
    assert item.finding == "A contractor dispute was reported."
    assert item.source_quality == "MEDIUM"  # thehindu.com is TIER_3

    stored = get_evidence_for_project(ingested_session, PROJECT_ID)
    assert len(stored) > 0
    assert stored[0].url == item.url


def test_rerun_is_idempotent_not_duplicated(ingested_session: Session) -> None:
    with (
        patch("app.services.web.service.search_web", return_value=FAKE_RESULTS),
        patch("app.services.web.service.extract_claims", side_effect=lambda results, **kw: _fake_claims(results)),
    ):
        get_web_intelligence(ingested_session, PROJECT_ID, force=True)
        get_web_intelligence(ingested_session, PROJECT_ID, force=True)

    stored = get_evidence_for_project(ingested_session, PROJECT_ID)
    urls = [row.url for row in stored]
    assert len(urls) == len(set(urls))  # no duplicate rows for the same URL/topic


def test_search_failure_degrades_gracefully(ingested_session: Session) -> None:
    with patch("app.services.web.service.search_web", side_effect=WebSearchUnavailableError("no key")):
        result = get_web_intelligence(ingested_session, PROJECT_ID, force=True)

    assert result.triggered is True
    assert result.evidence == []
    assert len(result.warnings) > 0


def test_project_not_found_raises() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as s:
        with pytest.raises(NotFoundError):
            get_web_intelligence(s, "does-not-exist", force=True)
