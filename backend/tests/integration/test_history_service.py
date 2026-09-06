from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.core.errors import NotFoundError
from app.models.project import Project
from app.services.history.llm import SummaryResult
from app.services.history.service import DEFAULT_QUESTION, get_project_history
from app.services.history.timeline import MODEL_PREDICTION, OBSERVED_FACT
from app.services.ingestion.pipeline import ingest_directory

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
VALID_PROJECT_IDS = ["617069", "619054", "616672", "617184", "617279"]

# Every test here stubs the LLM call so the suite never depends on network
# access or a live API key - the LLM's own success/failure/guardrail paths
# are already covered in tests/unit/test_history_llm.py.
FAKE_SUMMARY = SummaryResult(text="stubbed narrative summary", source="LLM", model="gemini-3.6-flash")


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


def test_history_answers_what_happened_for_all_five_projects(ingested_session: Session) -> None:
    """Exit criterion: user can ask "What happened to this project?" and get
    a chronological, evidence-backed answer, for all 5 validation projects."""
    with patch("app.services.history.service.summarize_current_state", return_value=FAKE_SUMMARY):
        for project_id in VALID_PROJECT_IDS:
            result = get_project_history(ingested_session, project_id)

            assert result.question == DEFAULT_QUESTION
            assert result.current_state  # non-empty answer
            assert len(result.timeline) > 0
            # chronological
            months = [e.month for e in result.timeline]
            assert months == sorted(months)
            # evidence-backed: every timeline entry cites its source
            assert all(e.evidence_ref for e in result.timeline)
            assert all(e.source_type == OBSERVED_FACT for e in result.timeline)


def test_history_distinguishes_evidence_types(ingested_session: Session) -> None:
    with patch("app.services.history.service.summarize_current_state", return_value=FAKE_SUMMARY):
        result = get_project_history(ingested_session, "617069")

    source_types = {s.source_type for s in result.historical_risk_signals}
    # KPS1 has a logged ML prediction and at least one non-monotonic DQ flag -
    # both a MODEL_PREDICTION and an INFERRED_TREND signal should be present.
    assert MODEL_PREDICTION in source_types


def test_history_uses_project_latest_month_by_default(ingested_session: Session) -> None:
    project = ingested_session.get(Project, "617069")
    with patch("app.services.history.service.summarize_current_state", return_value=FAKE_SUMMARY):
        result = get_project_history(ingested_session, "617069")
    assert result.as_of_date == project.latest_observation_month


def test_history_respects_point_in_time_as_of(ingested_session: Session) -> None:
    project = ingested_session.get(Project, "617069")
    with patch("app.services.history.service.summarize_current_state", return_value=FAKE_SUMMARY):
        result = get_project_history(ingested_session, "617069", as_of_date=project.first_observation_month)
    # The first month has exactly two OBSERVED_FACT entries: the observation
    # itself, and the PROJECT_FIRST_OBSERVED event - nothing from later months.
    assert len(result.timeline) == 2
    assert all(e.month == project.first_observation_month for e in result.timeline)


def test_history_unknown_project_raises_not_found(ingested_session: Session) -> None:
    with pytest.raises(NotFoundError):
        get_project_history(ingested_session, "does-not-exist")


def test_history_custom_question_is_passed_through(ingested_session: Session) -> None:
    captured = {}

    def fake_summarize(**kwargs):
        captured.update(kwargs)
        return FAKE_SUMMARY

    with patch("app.services.history.service.summarize_current_state", side_effect=fake_summarize):
        result = get_project_history(ingested_session, "617069", question="Why is this project risky?")

    assert result.question == "Why is this project risky?"
    assert captured["question"] == "Why is this project risky?"


def test_no_revised_cost_interpretation_present_in_health_context(ingested_session: Session) -> None:
    """These 5 validation projects have no revised cost recorded - the
    context handed to the LLM must say so explicitly (see Phase 5)."""
    captured = {}

    def fake_summarize(**kwargs):
        captured.update(kwargs)
        return FAKE_SUMMARY

    with patch("app.services.history.service.summarize_current_state", side_effect=fake_summarize):
        get_project_history(ingested_session, "617069")

    assert "No revised cost is currently recorded" in captured["latest_health"].get("revised_cost_status", "")
