"""Unit tests for Reporting MCP's deterministic Markdown renderer
(backend/app/mcp/reporting/markdown.py) - no LLM, no DB."""

from __future__ import annotations

from datetime import date

from app.mcp.reporting.markdown import render_markdown
from app.services.reporting.builder import Report

FULL_REPORT = Report(
    trace_id="trace-1",
    analysis_id="analysis-1",
    project_id="617069",
    project_name="Test Project",
    as_of_date=date(2026, 7, 1),
    executive_summary="This is the summary.",
    current_health={
        "overall_health": "WATCH", "cost_utilisation": 68.4, "schedule_utilisation": 74.2,
        "physical_progress": 52.1, "expected_progress": 74.2, "progress_gap": -22.1,
        "expenditure_progress_divergence": 16.3, "recent_trend": "STABLE",
    },
    cost_overrun_risk={"probability": 0.13, "risk_level": "LOW", "model_version": "cost-overrun-lightgbm-x"},
    time_overrun_risk={"status": "NOT_AVAILABLE", "reason": "No time-overrun prediction model is currently deployed."},
    key_changes=["Revised cost first appeared in March 2026."],
    top_risk_drivers=[{"rank": 1, "driver": "Schedule behind", "severity": "HIGH", "evidence_count": 3}],
    evidence=[
        {
            "category": "ANALYTICAL_INFERENCE", "description": "Progress gap is -22.1.",
            "confidence": 0.8, "source": "Health",
        }
    ],
    recommended_monitoring_actions=[
        {
            "priority": "HIGH", "action_type": "COST_PROGRESS_REVIEW",
            "action": "Review expenditure against physical achievement",
        }
    ],
    confidence={"diagnosis_confidence": 0.75},
    data_quality={"input_observation_count": 12},
    model_versions={"ml_model_version": "cost-overrun-lightgbm-x", "feature_version": "ml-fe-v1-reconstructed"},
    human_review_required=True,
    human_review_reason="Overall risk is CRITICAL.",
)

EMPTY_REPORT = Report(
    trace_id="trace-2",
    analysis_id="analysis-2",
    project_id="617069",
    project_name="Test Project",
    as_of_date=date(2026, 7, 1),
    executive_summary="Analysis for Test Project.",
    current_health=None,
    cost_overrun_risk=None,
    time_overrun_risk=None,
    key_changes=[],
    top_risk_drivers=[],
    evidence=[],
    recommended_monitoring_actions=[],
    confidence={},
    data_quality={},
    model_versions={},
    human_review_required=False,
    human_review_reason=None,
)

EXPECTED_HEADINGS = [
    "# Project Report: Test Project (617069)",
    "## Executive Summary",
    "## Current Health",
    "## Cost-Overrun Risk",
    "## Time-Overrun Risk",
    "## Key Changes",
    "## Top Risk Drivers",
    "## Evidence",
    "## Recommended Monitoring Actions",
    "## Confidence & Data Quality",
    "## Model Versions",
    "## Human Review",
]


def test_full_report_contains_every_section_in_order() -> None:
    markdown = render_markdown(FULL_REPORT)
    positions = [markdown.index(h) for h in EXPECTED_HEADINGS]
    assert positions == sorted(positions)
    assert "This is the summary." in markdown
    assert "Schedule behind" in markdown
    assert "Review expenditure against physical achievement" in markdown


def test_empty_report_renders_placeholders_not_crash() -> None:
    markdown = render_markdown(EMPTY_REPORT)
    for h in EXPECTED_HEADINGS:
        assert h in markdown
    assert "_Not computed for this report._" in markdown
    assert "_No drivers identified._" in markdown
    assert "_No evidence recorded._" in markdown
    assert "_No recommended actions._" in markdown
    assert "**Required:** False" in markdown
    assert "**Reason:** N/A" in markdown
