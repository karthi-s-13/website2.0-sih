"""Unit tests for Reporting MCP's deterministic PDF renderer
(backend/app/mcp/reporting/pdf.py) - no LLM, no DB."""

from __future__ import annotations

from datetime import date

import fitz

from app.mcp.reporting.pdf import render_pdf
from app.services.reporting.builder import Report


def _make_report(*, n_evidence: int = 1, n_drivers: int = 1) -> Report:
    return Report(
        trace_id="trace-1",
        analysis_id="analysis-1",
        project_id="617069",
        project_name="Test Project",
        as_of_date=date(2026, 7, 1),
        executive_summary="Short summary.",
        current_health={"overall_health": "WATCH"},
        cost_overrun_risk={"probability": 0.13, "risk_level": "LOW", "model_version": "v1"},
        time_overrun_risk=None,
        key_changes=["Change one."],
        top_risk_drivers=[
            {"rank": i, "driver": f"Driver {i} " * 5, "severity": "HIGH", "evidence_count": 2}
            for i in range(1, n_drivers + 1)
        ],
        evidence=[
            {
                "category": "REVIEW_REPORT", "description": "Some finding text. " * 10,
                "confidence": 0.5, "source": "doc.pdf p.3",
            }
            for _ in range(n_evidence)
        ],
        recommended_monitoring_actions=[{"priority": "HIGH", "action_type": "REVIEW", "action": "Review something."}],
        confidence={"diagnosis_confidence": 0.7},
        data_quality={"input_observation_count": 10},
        model_versions={"ml_model_version": "v1"},
        human_review_required=False,
        human_review_reason=None,
    )


def test_pdf_starts_with_pdf_signature() -> None:
    pdf_bytes = render_pdf(_make_report())
    assert pdf_bytes[:4] == b"%PDF"


def test_small_report_fits_on_one_page() -> None:
    pdf_bytes = render_pdf(_make_report())
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert doc.page_count == 1


def test_large_report_forces_multiple_pages() -> None:
    pdf_bytes = render_pdf(_make_report(n_evidence=80, n_drivers=40))
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    assert doc.page_count >= 2


def test_pdf_text_contains_project_name_and_summary() -> None:
    pdf_bytes = render_pdf(_make_report())
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)
    assert "Test Project" in full_text
    assert "Short summary." in full_text
