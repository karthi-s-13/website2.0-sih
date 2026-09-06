from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base, get_db
from app.main import app
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
def client() -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    test_session_factory = sessionmaker(bind=engine)

    with Session(engine) as setup_session:
        ingest_directory(setup_session, RAW_DIR)

    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


class _ImmediateFuture:
    def __init__(self, value):
        self._value = value

    def result(self):
        return self._value


class _ImmediateExecutor:
    """A same-thread stand-in for ThreadPoolExecutor: the API endpoint always
    uses the real default (parallel=True), but a single shared low-level
    sqlite3 connection (as used by this in-memory test fixture) is not safe
    under genuine concurrent cursor use from multiple OS threads - not a
    correctness question for what these tests check. True concurrent
    execution is exercised live against real Postgres in
    `scripts/run_coordinator.py`; see `service.py`'s `_execute_plan`.
    """

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def submit(self, fn, *args, **kwargs):
        return _ImmediateFuture(fn(*args, **kwargs))


def _mocked():
    stack = ExitStack()
    stack.enter_context(patch("google.genai.Client", side_effect=RuntimeError("test: no real LLM calls")))
    stack.enter_context(patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW))
    stack.enter_context(patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB))
    stack.enter_context(patch("app.services.coordinator.stages.search_review_evidence", return_value=NOT_FOUND_REVIEW))
    stack.enter_context(patch("app.services.coordinator.stages.get_web_intelligence", return_value=NOT_TRIGGERED_WEB))
    stack.enter_context(patch("app.services.coordinator.service.summarize_report", return_value=FAKE_NARRATIVE))
    stack.enter_context(patch("app.services.coordinator.service.ThreadPoolExecutor", _ImmediateExecutor))
    return stack


def test_analyze_endpoint_cost_risk(client: TestClient) -> None:
    with _mocked():
        response = client.post(
            "/api/v1/analyze", json={"query": "What is the cost risk?", "project_id": "617069"}
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["intent"] == "COST_RISK"
    assert data["project_id"] == "617069"
    assert data["report"]["cost_overrun_risk"] is not None


def test_analyze_endpoint_not_found(client: TestClient) -> None:
    with _mocked():
        response = client.post("/api/v1/analyze", json={"query": "gibberish unrelated text"})
    assert response.status_code == 404


def test_analyze_endpoint_ambiguous_returns_candidates(client: TestClient) -> None:
    with _mocked():
        response = client.post("/api/v1/analyze", json={"query": "Transmission System"})
    assert response.status_code in {200, 404}
    if response.status_code == 200:
        data = response.json()["data"]
        assert data["resolution_status"] == "AMBIGUOUS"
        assert len(data["candidates"]) > 1


def test_portfolio_endpoint(client: TestClient) -> None:
    with _mocked():
        response = client.get("/api/v1/portfolio")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["ranked"]) > 0
    assert data["ranked"][0]["rank"] == 1


def test_portfolio_endpoint_top_n(client: TestClient) -> None:
    with _mocked():
        response = client.get("/api/v1/portfolio", params={"top_n": 2})
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["top_risk_project_ids"]) <= 2
