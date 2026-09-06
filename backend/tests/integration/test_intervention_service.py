from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.core.errors import NotFoundError
from app.services.ingestion.pipeline import ingest_directory
from app.services.intervention.mapping import ALL_ACTION_TYPES, assert_not_administrative_decision
from app.services.intervention.service import recommend_interventions
from app.services.rag.service import EvidenceResult
from app.services.web.service import WebIntelligenceResult

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
VALID_PROJECT_IDS = ["617069", "619054", "616672", "617184", "617279"]

NOT_FOUND_REVIEW = EvidenceResult(
    project_id="x", project_name="x", question="q", answer="not mentioned", citations=[],
    summary_source="DETERMINISTIC_FALLBACK", summary_model=None, evidence_found=False,
    searched_at="2026-07-01T00:00:00Z",
)
NOT_TRIGGERED_WEB = WebIntelligenceResult(
    project_id="x", project_name="x", triggered=False, trigger_reason="not high risk",
    topics_searched=[], evidence=[], warnings=[], searched_at="2026-07-01T00:00:00Z",
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


def test_interventions_for_all_five_projects(ingested_session: Session) -> None:
    with (
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
    ):
        for project_id in VALID_PROJECT_IDS:
            result = recommend_interventions(ingested_session, project_id)
            assert result.project_id == project_id
            assert result.suggested_monitoring_level in {"NORMAL", "ENHANCED", "PRIORITY", "CRITICAL"}
            for rec in result.recommendations:
                assert rec.action_type in ALL_ACTION_TYPES
                assert rec.action
                assert rec.reason
                assert rec.review_area
                # FR-027: never claim an action has been performed / an
                # autonomous administrative decision.
                assert_not_administrative_decision(rec.action)
                assert_not_administrative_decision(rec.reason)


def test_every_driver_produces_a_recommendation(ingested_session: Session) -> None:
    with (
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
    ):
        from app.services.diagnosis.service import diagnose_project

        diagnosis = diagnose_project(ingested_session, "617069")
        result = recommend_interventions(ingested_session, "617069")

    driver_labels_with_recs = {r.driver for r in result.recommendations if r.driver}
    for d in diagnosis.drivers:
        assert d.driver in driver_labels_with_recs


def test_recommendation_evidence_ids_resolve_to_real_evidence(ingested_session: Session) -> None:
    with (
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
    ):
        from app.services.diagnosis.service import diagnose_project

        diagnosis = diagnose_project(ingested_session, "617069")
        result = recommend_interventions(ingested_session, "617069")

    known_ids = {e.evidence_id for e in diagnosis.evidence}
    for rec in result.recommendations:
        assert len(rec.evidence_ids) > 0
        assert all(eid in known_ids for eid in rec.evidence_ids)


def test_project_not_found_raises(session: Session) -> None:
    with pytest.raises(NotFoundError):
        recommend_interventions(session, "does-not-exist")


def test_recommendations_are_reproducible(ingested_session: Session) -> None:
    with (
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
    ):
        first = recommend_interventions(ingested_session, "617069", as_of_date=date(2026, 7, 1))
        second = recommend_interventions(ingested_session, "617069", as_of_date=date(2026, 7, 1))
    assert [r.action for r in first.recommendations] == [r.action for r in second.recommendations]
    assert first.suggested_monitoring_level == second.suggested_monitoring_level
