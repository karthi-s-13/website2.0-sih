from contextlib import ExitStack
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.core.errors import NotFoundError
from app.services.coordinator.intent import COMPLETE_PROJECT_ANALYSIS, COST_RISK, PROJECT_HEALTH
from app.services.coordinator.resolution import AMBIGUOUS
from app.services.coordinator.service import run_analysis
from app.services.ingestion.pipeline import ingest_directory
from app.services.rag.service import EvidenceResult
from app.services.reporting.narrative import NarrativeResult
from app.services.web.service import WebIntelligenceResult

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"

NOT_FOUND_REVIEW = EvidenceResult(
    project_id="x", project_name="x", question="q", answer="not mentioned", citations=[],
    summary_source="DETERMINISTIC_FALLBACK", summary_model=None, evidence_found=False,
    searched_at="2026-07-01T00:00:00Z",
)
NOT_TRIGGERED_WEB = WebIntelligenceResult(
    project_id="x", project_name="x", triggered=False, trigger_reason="not high risk",
    topics_searched=[], evidence=[], warnings=[], searched_at="2026-07-01T00:00:00Z",
)
FAKE_NARRATIVE = NarrativeResult(text="stubbed executive summary", source="LLM", model="gemini-3.6-flash")


@pytest.fixture
def session() -> Session:
    # StaticPool + check_same_thread=False purely so create_all/queries from
    # different pytest internals don't trip over sqlite's default thread
    # affinity; the coordinator's own genuine thread-parallel path is never
    # exercised here (tests call run_analysis with parallel=False) since a
    # single shared sqlite3 connection is not safe under real concurrent
    # cursor use - see service.py's `_execute_plan` docstring.
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def ingested_session(session: Session) -> Session:
    ingest_directory(session, RAW_DIR)
    return session


def _mocked():
    """Every external dependency the Coordinator can reach: review/web
    evidence (both the direct WEB/REVIEW stages and Phase 9's internal use
    of them via diagnose_project), and the Reporting Agent's LLM narrative -
    hermetic, no network calls, matching every prior phase's test approach.
    """
    stack = ExitStack()
    # No real LLM calls anywhere (intent classification, claim extraction,
    # etc. all fall back to their deterministic paths) - keeps the suite
    # hermetic and fast instead of waiting out a real free-tier rate limit.
    stack.enter_context(patch("google.genai.Client", side_effect=RuntimeError("test: no real LLM calls")))
    stack.enter_context(patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW))
    stack.enter_context(patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB))
    stack.enter_context(patch("app.services.coordinator.stages.search_review_evidence", return_value=NOT_FOUND_REVIEW))
    stack.enter_context(patch("app.services.coordinator.stages.get_web_intelligence", return_value=NOT_TRIGGERED_WEB))
    stack.enter_context(patch("app.services.coordinator.service.summarize_report", return_value=FAKE_NARRATIVE))
    return stack


def test_cost_risk_query_runs_narrow_plan(ingested_session: Session) -> None:
    with _mocked():
        state = run_analysis(ingested_session, "What is the cost risk?", project_id="617069", parallel=False)
    assert state.intent == COST_RISK
    assert state.plan == ["PROJECT", "PREDICTION"]
    assert state.prediction is not None or state.prediction_error
    assert state.history is None  # narrow plan never ran History
    assert state.report is not None
    assert state.report.cost_overrun_risk is not None


def test_health_query_runs_narrow_plan(ingested_session: Session) -> None:
    with _mocked():
        state = run_analysis(ingested_session, "What is the current health?", project_id="617069", parallel=False)
    assert state.intent == PROJECT_HEALTH
    assert state.plan == ["PROJECT", "HEALTH"]
    assert state.health is not None
    assert state.report.current_health is not None


def test_complete_analysis_runs_full_plan(ingested_session: Session) -> None:
    with _mocked():
        state = run_analysis(
            ingested_session, "Give me a complete analysis of this project.", project_id="617069", parallel=False
        )
    assert state.intent == COMPLETE_PROJECT_ANALYSIS
    assert state.history is not None
    assert state.diagnosis is not None
    assert state.intervention is not None
    assert state.report.top_risk_drivers is not None


def test_explicit_project_id_skips_resolution_ambiguity(ingested_session: Session) -> None:
    with _mocked():
        state = run_analysis(ingested_session, "anything at all", project_id="619054", parallel=False)
    assert state.project_id == "619054"
    assert state.resolution_status == "RESOLVED"


def test_ambiguous_or_unresolvable_free_text_never_silently_guesses(ingested_session: Session) -> None:
    # A query naming no project distinctly enough must come back AMBIGUOUS
    # (state returned with candidates) or NOT_FOUND (raised) - never
    # silently guess a project.
    with _mocked():
        try:
            state = run_analysis(ingested_session, "Transmission System", parallel=False)
        except NotFoundError:
            return
    assert state.resolution_status == AMBIGUOUS
    assert state.report is None
    assert len(state.candidates) > 1


def test_unresolvable_project_raises_not_found(ingested_session: Session) -> None:
    with pytest.raises(NotFoundError):
        run_analysis(ingested_session, "completely unrelated gibberish query", parallel=False)


def test_risk_triggered_expansion(ingested_session: Session) -> None:
    import app.services.health.service as health_service

    real_health = health_service.get_project_health(ingested_session, "617069", date(2026, 7, 1))
    critical_health = real_health.__class__(**{**real_health.__dict__, "overall_health": "CRITICAL"})

    with _mocked(), patch("app.services.coordinator.stages.get_project_health", return_value=critical_health):
        state = run_analysis(ingested_session, "What is the current health?", project_id="617069", parallel=False)

    assert state.expanded is True
    assert "INTERVENTION" in state.plan
    assert state.history is not None


def test_stage_results_recorded(ingested_session: Session) -> None:
    with _mocked():
        state = run_analysis(ingested_session, "What is the cost risk?", project_id="617069", parallel=False)
    assert len(state.stage_results) > 0
    for sr in state.stage_results:
        assert sr.status in {"SUCCESS", "FAILED", "SKIPPED"}


def test_portfolio_intent_routes_to_batch_ranking(ingested_session: Session) -> None:
    with _mocked():
        state = run_analysis(ingested_session, "Show me the portfolio risk ranking across all projects", parallel=False)
    assert state.portfolio is not None
    assert len(state.portfolio.ranked) > 0
    assert state.report is None
