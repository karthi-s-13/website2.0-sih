"""Intent Classification (spec section 6): the Coordinator's entry point,
mapping a free-text query onto one of thirteen intents. One bounded Gemini
call (same guardrail shape as `history/llm.py`) whose output must be
exactly one of the thirteen valid strings; a deterministic keyword-based
fallback covers no API key / a failed call / an invalid output - the
Coordinator must never fail to classify, just fall back to a safe default.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PROJECT_LOOKUP = "PROJECT_LOOKUP"
PROJECT_HISTORY = "PROJECT_HISTORY"
PROJECT_HEALTH = "PROJECT_HEALTH"
COST_RISK = "COST_RISK"
TIME_RISK = "TIME_RISK"
ANOMALY_ANALYSIS = "ANOMALY_ANALYSIS"
REVIEW_REPORT_QUERY = "REVIEW_REPORT_QUERY"
WEB_INTELLIGENCE = "WEB_INTELLIGENCE"
RISK_ANALYSIS = "RISK_ANALYSIS"
INTERVENTION = "INTERVENTION"
MONTHLY_CHANGE = "MONTHLY_CHANGE"
PORTFOLIO_ANALYSIS = "PORTFOLIO_ANALYSIS"
COMPLETE_PROJECT_ANALYSIS = "COMPLETE_PROJECT_ANALYSIS"
REPORT_GENERATION = "REPORT_GENERATION"

ALL_INTENTS = [
    PROJECT_LOOKUP,
    PROJECT_HISTORY,
    PROJECT_HEALTH,
    COST_RISK,
    TIME_RISK,
    ANOMALY_ANALYSIS,
    REVIEW_REPORT_QUERY,
    WEB_INTELLIGENCE,
    RISK_ANALYSIS,
    INTERVENTION,
    MONTHLY_CHANGE,
    PORTFOLIO_ANALYSIS,
    COMPLETE_PROJECT_ANALYSIS,
    REPORT_GENERATION,
]

DEFAULT_INTENT = COMPLETE_PROJECT_ANALYSIS

SYSTEM_INSTRUCTION = """You classify a user's question about an infrastructure project monitoring \
platform into exactly one intent. Respond with ONLY the intent string, nothing else - no \
punctuation, no explanation.

Valid intents:
  PROJECT_LOOKUP            - basic project facts (name, agency, cost, dates)
  PROJECT_HISTORY           - what happened / timeline
  PROJECT_HEALTH            - current health / progress vs schedule
  COST_RISK                 - cost-overrun probability
  TIME_RISK                 - schedule/time-overrun probability
  ANOMALY_ANALYSIS          - unusual patterns in the data
  REVIEW_REPORT_QUERY       - what official review reports say
  WEB_INTELLIGENCE          - external/news evidence
  RISK_ANALYSIS             - why is this project risky (drivers), no action recommendations
  INTERVENTION              - what monitoring actions should be taken
  MONTHLY_CHANGE            - what changed recently
  PORTFOLIO_ANALYSIS        - about multiple/all projects, not one
  COMPLETE_PROJECT_ANALYSIS - a full end-to-end analysis of one project
  REPORT_GENERATION         - an explicit request for a full report/decision package

Example: "Why is Project X at high risk and what should we do?" -> COMPLETE_PROJECT_ANALYSIS
Example: "What is the cost risk?" -> COST_RISK
"""

# Deterministic fallback: ordered (pattern, intent) - first match wins.
_KEYWORD_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bportfolio\b|\ball projects\b|\bevery project\b", re.I), PORTFOLIO_ANALYSIS),
    (re.compile(r"\brecommend|what should (we|i) do|next steps|intervention", re.I), INTERVENTION),
    (re.compile(r"\bwhy\b.*\brisk\b|risk driver|diagnos", re.I), RISK_ANALYSIS),
    (re.compile(r"\bchanged\b|\bchange\b|since last month", re.I), MONTHLY_CHANGE),
    (re.compile(r"\btime.?overrun\b|\bschedule risk\b|\bdelay probability\b", re.I), TIME_RISK),
    (re.compile(r"\bcost.?overrun\b|\bcost risk\b", re.I), COST_RISK),
    (re.compile(r"\bhealth\b|\bprogress\b", re.I), PROJECT_HEALTH),
    (re.compile(r"\bhistory\b|\bhappened\b|\btimeline\b", re.I), PROJECT_HISTORY),
    (re.compile(r"\banomal", re.I), ANOMALY_ANALYSIS),
    (re.compile(r"\breview report\b|\bofficial report\b", re.I), REVIEW_REPORT_QUERY),
    (re.compile(r"\bweb\b|\bnews\b|\bexternal\b", re.I), WEB_INTELLIGENCE),
    (re.compile(r"\breport\b", re.I), REPORT_GENERATION),
    (re.compile(r"\bwho is\b|\bwhat is\b.*\bproject\b|\blookup\b", re.I), PROJECT_LOOKUP),
]


@dataclass(frozen=True)
class IntentResult:
    intent: str
    source: str  # "LLM" | "KEYWORD_FALLBACK"


def _keyword_fallback(query: str) -> str:
    for pattern, intent in _KEYWORD_RULES:
        if pattern.search(query):
            return intent
    return DEFAULT_INTENT


def classify_intent(query: str, *, api_key: str | None, model: str) -> IntentResult:
    fallback = IntentResult(intent=_keyword_fallback(query), source="KEYWORD_FALLBACK")

    if not api_key:
        return fallback

    try:
        from app.services.llm.groq_client import generate_text

        text = generate_text(
            api_key=api_key, model=model, system_instruction=SYSTEM_INSTRUCTION, contents=query, temperature=0.0
        ).upper()
    except Exception:  # noqa: BLE001 - must degrade gracefully, never raise
        return fallback

    if text not in ALL_INTENTS:
        return fallback

    return IntentResult(intent=text, source="LLM")
