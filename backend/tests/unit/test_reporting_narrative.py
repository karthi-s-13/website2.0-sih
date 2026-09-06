from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.health.formulas import HealthVector, MilestoneHealth, RecentTrend
from app.services.reporting.narrative import summarize_report

SNAPSHOT = date(2026, 7, 1)

HEALTH = HealthVector(
    snapshot_month=SNAPSHOT, overall_health="CRITICAL", cost_utilisation=80.0, schedule_utilisation=50.0,
    physical_progress=20.0, expected_progress=50.0, progress_gap=-30.0, expenditure_progress_divergence=60.0,
    recent_trend=RecentTrend(1.0, 5.0, 1.0, 5.0, 0, "DECLINING"),
    milestone_health=MilestoneHealth(status="NOT_AVAILABLE", total=0, completed=0, delayed=0),
    input_observation_count=6,
)
PREDICTION = SimpleNamespace(
    project_id="p1", prediction_date="2026-07-01", risk_type="cost_overrun", probability=0.9,
    risk_level="CRITICAL", model_version="m1", feature_version="features-v1", leakage_check="PASSED",
)


def test_no_api_key_uses_fallback() -> None:
    result = summarize_report(
        api_key=None, model="gemini-3.6-flash", project_name="Test Project", health=HEALTH, prediction=PREDICTION,
    )
    assert result.source == "DETERMINISTIC_FALLBACK"
    assert result.model is None
    assert "Test Project" in result.text
    assert "CRITICAL" in result.text


def test_fallback_with_nothing_computed() -> None:
    result = summarize_report(api_key=None, model="gemini-3.6-flash", project_name="Test Project", health=None, prediction=None)
    assert result.text == "Analysis for Test Project."


def test_llm_failure_falls_back() -> None:
    with patch("google.genai.Client", side_effect=RuntimeError("network down")):
        result = summarize_report(
            api_key="fake-key", model="gemini-3.6-flash", project_name="Test Project", health=HEALTH, prediction=PREDICTION,
        )
    assert result.source == "DETERMINISTIC_FALLBACK"


def test_llm_success_uses_llm_text() -> None:
    fake_response = MagicMock()
    fake_response.text = "The project is in critical health with high cost-overrun risk."
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client):
        result = summarize_report(
            api_key="fake-key", model="gemini-3.6-flash", project_name="Test Project", health=HEALTH, prediction=PREDICTION,
        )
    assert result.source == "LLM"
    assert result.model == "gemini-3.6-flash"


def test_guardrail_blocks_definitive_claim() -> None:
    fake_response = MagicMock()
    fake_response.text = "This project will definitely overrun its budget."
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client):
        result = summarize_report(
            api_key="fake-key", model="gemini-3.6-flash", project_name="Test Project", health=HEALTH, prediction=PREDICTION,
        )
    assert result.source == "DETERMINISTIC_FALLBACK"


def test_guardrail_blocks_performed_claim() -> None:
    fake_response = MagicMock()
    fake_response.text = "The recommended action has been performed."
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client):
        result = summarize_report(
            api_key="fake-key", model="gemini-3.6-flash", project_name="Test Project", health=HEALTH, prediction=PREDICTION,
        )
    assert result.source == "DETERMINISTIC_FALLBACK"
