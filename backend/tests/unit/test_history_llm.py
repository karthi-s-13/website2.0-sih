from datetime import date
from unittest.mock import MagicMock, patch

from app.services.history.llm import (
    deterministic_fallback_summary,
    summarize_current_state,
)
from app.services.history.timeline import MajorChange, RiskSignal, TimelineEntry

TIMELINE = [
    TimelineEntry(
        month=date(2025, 7, 1),
        title="Monthly observation recorded",
        description="Cumulative expenditure ₹6.99 Cr; physical progress 0.0%.",
        source_type="OBSERVED_FACT",
        evidence_ref="project_monthly_observations:2025-07-01",
    ),
    TimelineEntry(
        month=date(2025, 8, 1),
        title="Monthly observation recorded",
        description="Cumulative expenditure ₹13.99 Cr; physical progress 1.0%.",
        source_type="OBSERVED_FACT",
        evidence_ref="project_monthly_observations:2025-08-01",
    ),
]
MAJOR_CHANGES = [
    MajorChange(
        month=date(2025, 8, 1),
        change_type="COST_REVISED",
        description="Revised cost changed.",
        source_type="OBSERVED_FACT",
        previous_value=None,
        new_value="466.0",
    )
]
RISK_SIGNALS = [
    RiskSignal(
        month=date(2025, 8, 1),
        signal_type="ML_COST_OVERRUN_PROBABILITY",
        description="Model x estimates a 13.0% probability of future cost overrun (LOW risk level).",
        source_type="MODEL_PREDICTION",
        severity="LOW",
    )
]


def test_deterministic_fallback_summary_empty_timeline() -> None:
    text = deterministic_fallback_summary("Test Project", [], [], [])
    assert "No observation history" in text


def test_deterministic_fallback_summary_includes_key_facts() -> None:
    text = deterministic_fallback_summary("Test Project", TIMELINE, MAJOR_CHANGES, RISK_SIGNALS)
    assert "Test Project" in text
    assert "2025-07-01" in text
    assert "2025-08-01" in text
    assert "13.0%" in text  # the model prediction signal is surfaced


def test_summarize_current_state_no_api_key_uses_fallback() -> None:
    result = summarize_current_state(
        api_key=None,
        model="gemini-3.6-flash",
        project_name="Test Project",
        question="What happened to this project?",
        timeline=TIMELINE,
        major_changes=MAJOR_CHANGES,
        risk_signals=RISK_SIGNALS,
        latest_health={},
    )
    assert result.source == "DETERMINISTIC_FALLBACK"
    assert result.model is None
    assert "Test Project" in result.text


def test_summarize_current_state_llm_failure_falls_back() -> None:
    with patch("google.genai.Client", side_effect=RuntimeError("network down")):
        result = summarize_current_state(
            api_key="fake-key",
            model="gemini-3.6-flash",
            project_name="Test Project",
            question="What happened to this project?",
            timeline=TIMELINE,
            major_changes=MAJOR_CHANGES,
            risk_signals=RISK_SIGNALS,
            latest_health={},
        )
    assert result.source == "DETERMINISTIC_FALLBACK"


def test_summarize_current_state_success_uses_llm_text() -> None:
    fake_response = MagicMock()
    fake_response.text = "The project has made steady progress since July 2025."
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client):
        result = summarize_current_state(
            api_key="fake-key",
            model="gemini-3.6-flash",
            project_name="Test Project",
            question="What happened to this project?",
            timeline=TIMELINE,
            major_changes=MAJOR_CHANGES,
            risk_signals=RISK_SIGNALS,
            latest_health={},
        )
    assert result.source == "LLM"
    assert result.model == "gemini-3.6-flash"
    assert result.text == "The project has made steady progress since July 2025."


def test_summarize_current_state_guardrail_blocks_definitive_claim() -> None:
    fake_response = MagicMock()
    fake_response.text = "This project will definitely overrun its budget."
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client):
        result = summarize_current_state(
            api_key="fake-key",
            model="gemini-3.6-flash",
            project_name="Test Project",
            question="What happened to this project?",
            timeline=TIMELINE,
            major_changes=MAJOR_CHANGES,
            risk_signals=RISK_SIGNALS,
            latest_health={},
        )
    assert result.source == "DETERMINISTIC_FALLBACK"  # guardrail rejected the LLM output


def test_summarize_current_state_guardrail_blocks_definitive_safety_claim() -> None:
    fake_response = MagicMock()
    fake_response.text = "This project will definitely not overrun."
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client):
        result = summarize_current_state(
            api_key="fake-key",
            model="gemini-3.6-flash",
            project_name="Test Project",
            question="What happened to this project?",
            timeline=TIMELINE,
            major_changes=MAJOR_CHANGES,
            risk_signals=RISK_SIGNALS,
            latest_health={},
        )
    assert result.source == "DETERMINISTIC_FALLBACK"
