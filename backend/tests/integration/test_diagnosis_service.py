from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.core.errors import NotFoundError
from app.services.diagnosis.service import diagnose_project
from app.services.ingestion.pipeline import ingest_directory
from app.services.rag.service import EvidenceResult
from app.services.web.service import WebIntelligenceResult

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
VALID_PROJECT_IDS = ["617069", "619054", "616672", "617184", "617279"]

NOT_FOUND_REVIEW = EvidenceResult(
    project_id="x",
    project_name="x",
    question="q",
    answer="not mentioned",
    citations=[],
    summary_source="DETERMINISTIC_FALLBACK",
    summary_model=None,
    evidence_found=False,
    searched_at="2026-07-01T00:00:00Z",
)

NOT_TRIGGERED_WEB = WebIntelligenceResult(
    project_id="x",
    project_name="x",
    triggered=False,
    trigger_reason="not high risk",
    topics_searched=[],
    evidence=[],
    warnings=[],
    searched_at="2026-07-01T00:00:00Z",
)


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


def test_diagnosis_for_all_five_projects(ingested_session: Session) -> None:
    with (
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
    ):
        for project_id in VALID_PROJECT_IDS:
            result = diagnose_project(ingested_session, project_id)
            assert result.project_id == project_id
            assert result.overall_risk in {"LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL", "DATA_NOT_AVAILABLE"}
            assert 0.0 <= result.confidence <= 1.0
            # Exit criterion: every driver has supporting evidence.
            evidence_ids = {e.evidence_id for e in result.evidence}
            for driver in result.drivers:
                assert len(driver.evidence_ids) > 0
                assert all(eid in evidence_ids for eid in driver.evidence_ids)
            # No evidence item mixes categories with a source it doesn't belong to.
            for e in result.evidence:
                assert e.category in {
                    "PAIMANA_STRUCTURED_DATA",
                    "ANALYTICAL_INFERENCE",
                    "MODEL_INFERENCE",
                    "REVIEW_REPORT",
                    "OFFICIAL_EXTERNAL_SOURCE",
                    "SECONDARY_SOURCE",
                }


def test_driver_ranks_are_sequential(ingested_session: Session) -> None:
    with (
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
    ):
        result = diagnose_project(ingested_session, "617069")
    assert [d.rank for d in result.drivers] == list(range(1, len(result.drivers) + 1))


def test_include_web_false_skips_web_call(ingested_session: Session) -> None:
    with (
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence") as mock_web,
    ):
        diagnose_project(ingested_session, "617069", include_web=False)
    mock_web.assert_not_called()


def test_project_not_found_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        diagnose_project(session, "does-not-exist")


def test_diagnosis_is_reproducible(ingested_session: Session) -> None:
    with (
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
    ):
        first = diagnose_project(ingested_session, "617069", as_of_date=date(2026, 7, 1))
        second = diagnose_project(ingested_session, "617069", as_of_date=date(2026, 7, 1))
    assert first.overall_risk == second.overall_risk
    assert first.risk_score == second.risk_score
    assert [d.driver for d in first.drivers] == [d.driver for d in second.drivers]
    assert [e.evidence_id for e in first.evidence] == [e.evidence_id for e in second.evidence]
