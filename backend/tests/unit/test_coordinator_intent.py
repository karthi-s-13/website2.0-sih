from unittest.mock import patch

from app.services.coordinator.intent import (
    ANOMALY_ANALYSIS,
    COMPLETE_PROJECT_ANALYSIS,
    COST_RISK,
    DEFAULT_INTENT,
    INTERVENTION,
    MONTHLY_CHANGE,
    PORTFOLIO_ANALYSIS,
    PROJECT_HEALTH,
    PROJECT_HISTORY,
    RISK_ANALYSIS,
    WEB_INTELLIGENCE,
    classify_intent,
)


def test_no_api_key_uses_keyword_fallback() -> None:
    result = classify_intent("What is the cost risk?", api_key=None, model="gemini-3.6-flash")
    assert result.intent == COST_RISK
    assert result.source == "KEYWORD_FALLBACK"


def test_keyword_fallback_health_query() -> None:
    result = classify_intent("What is the current health of this project?", api_key=None, model="gemini-3.6-flash")
    assert result.intent == PROJECT_HEALTH


def test_keyword_fallback_history() -> None:
    result = classify_intent("What happened to this project?", api_key=None, model="gemini-3.6-flash")
    assert result.intent == PROJECT_HISTORY


def test_keyword_fallback_intervention() -> None:
    result = classify_intent("What should we do about this?", api_key=None, model="gemini-3.6-flash")
    assert result.intent == INTERVENTION


def test_keyword_fallback_risk_analysis() -> None:
    result = classify_intent("Why is this project at risk?", api_key=None, model="gemini-3.6-flash")
    assert result.intent == RISK_ANALYSIS


def test_keyword_fallback_portfolio() -> None:
    result = classify_intent("Show me the portfolio risk ranking", api_key=None, model="gemini-3.6-flash")
    assert result.intent == PORTFOLIO_ANALYSIS


def test_keyword_fallback_anomaly() -> None:
    result = classify_intent("Are there any anomalies?", api_key=None, model="gemini-3.6-flash")
    assert result.intent == ANOMALY_ANALYSIS


def test_keyword_fallback_web() -> None:
    result = classify_intent("Any relevant news or external evidence?", api_key=None, model="gemini-3.6-flash")
    assert result.intent == WEB_INTELLIGENCE


def test_keyword_fallback_monthly_change() -> None:
    result = classify_intent("What changed since last month?", api_key=None, model="gemini-3.6-flash")
    assert result.intent == MONTHLY_CHANGE


def test_keyword_fallback_default_for_unclassifiable_query() -> None:
    result = classify_intent("asdf qwerty", api_key=None, model="gemini-3.6-flash")
    assert result.intent == DEFAULT_INTENT == COMPLETE_PROJECT_ANALYSIS


def test_llm_failure_falls_back() -> None:
    with patch("app.services.llm.groq_client.generate_text", side_effect=RuntimeError("network down")):
        result = classify_intent("What is the cost risk?", api_key="fake-key", model="gemini-3.6-flash")
    assert result.source == "KEYWORD_FALLBACK"
    assert result.intent == COST_RISK


def test_llm_success_returns_valid_intent() -> None:
    with patch("app.services.llm.groq_client.generate_text", return_value="COMPLETE_PROJECT_ANALYSIS"):
        result = classify_intent(
            "Why is Project X at high risk and what should we do?", api_key="fake-key", model="gemini-3.6-flash"
        )
    assert result.source == "LLM"
    assert result.intent == COMPLETE_PROJECT_ANALYSIS


def test_llm_invalid_output_falls_back() -> None:
    with patch("app.services.llm.groq_client.generate_text", return_value="NOT_A_REAL_INTENT"):
        result = classify_intent("What is the cost risk?", api_key="fake-key", model="gemini-3.6-flash")
    assert result.source == "KEYWORD_FALLBACK"
    assert result.intent == COST_RISK
