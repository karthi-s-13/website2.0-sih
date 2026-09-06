"""Integration tests for Reporting MCP (backend/app/mcp/reporting/service.py)
against a hermetic sqlite fixture - LLM/web calls mocked, same pattern as
test_intervention_service.py. The key regression test here is that
current_health/cost_overrun_risk are populated (the gap Coordinator's own
FULL_PLAN sequence alone would leave null - see orchestration.py's
docstring)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.services.ingestion.pipeline import ingest_directory
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
def test_sessionmaker():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    ingest_directory(maker(), RAW_DIR)
    return maker


@pytest.fixture
def mcp_session(test_sessionmaker):
    # Same hermetic pattern as test_coordinator_service.py: blocking the LLM
    # client entirely forces every LLM-touched call (history's narrative,
    # reporting's executive summary) to its deterministic fallback, rather
    # than making real Gemini calls in every test.
    with (
        patch("app.mcp._shared.SessionLocal", test_sessionmaker),
        patch("app.services.llm.groq_client.generate_text", side_effect=RuntimeError("test: no real LLM calls")),
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
        patch("app.services.coordinator.stages.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.coordinator.stages.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
    ):
        yield


def test_generate_json_report_populates_health_and_prediction(mcp_session) -> None:
    """The regression test for the FULL_PLAN gap-fix: generate_json_report
    must have non-null current_health/cost_overrun_risk, unlike a bare
    Coordinator FULL_PLAN (PROJECT, HISTORY, INTERVENTION_CALL) run alone."""
    from app.mcp.reporting.service import generate_json_report

    for project_id in VALID_PROJECT_IDS:
        result = generate_json_report(project_id)
        assert result.status == "OK"
        assert result.report["current_health"] is not None
        assert result.report["cost_overrun_risk"] is not None
        assert result.report["project_id"] == project_id


def test_generate_json_report_not_found(mcp_session) -> None:
    from app.mcp.reporting.service import generate_json_report

    result = generate_json_report("does-not-exist")
    assert result.status == "NOT_FOUND"


def test_generate_markdown_report_contains_project_name_and_sections(mcp_session) -> None:
    from app.mcp.reporting.service import generate_markdown_report

    result = generate_markdown_report(VALID_PROJECT_IDS[0])
    assert result.status == "OK"
    assert "## Current Health" in result.markdown
    assert "## Cost-Overrun Risk" in result.markdown


def test_generate_pdf_report_produces_valid_pdf(mcp_session) -> None:
    import base64

    import fitz

    from app.mcp.reporting.service import generate_pdf_report

    result = generate_pdf_report(VALID_PROJECT_IDS[0])
    assert result.status == "OK"
    pdf_bytes = base64.b64decode(result.pdf_base64)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert doc.page_count == result.page_count
    assert doc.page_count >= 1


def test_generate_executive_summary_falls_back_without_api_key(mcp_session) -> None:
    from unittest.mock import MagicMock

    from app.mcp.reporting.service import generate_executive_summary

    fake_settings = MagicMock(gemini_api_key=None, gemini_model="gemini-3.6-flash")
    with patch("app.mcp.reporting.service.get_settings", return_value=fake_settings):
        result = generate_executive_summary(VALID_PROJECT_IDS[0])

    assert result.status == "OK"
    assert result.source == "DETERMINISTIC_FALLBACK"
    assert result.text
