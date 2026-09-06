"""Executive-summary narrative synthesis (spec section 26's first required
section; the four-question format of section 64). The only LLM call in the
Reporting Agent - it writes a short paragraph grounded strictly in the
already-computed, deterministic results passed in; it never computes a
fact, trend, prediction, or risk driver of its own. Same guardrail shape as
`history/llm.py`/`rag/answer.py`/`web/claim_extraction.py`: no API key, a
failed call, or an ungrounded/guardrail-violating output falls back to a
deterministic template summary.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.diagnosis.service import DiagnosisResult
from app.services.health.formulas import HealthVector
from app.services.history.service import HistoryResult
from app.services.intervention.service import InterventionResult
from app.services.prediction.service import PredictionResult

FORBIDDEN_PHRASES = [
    "will definitely not overrun",
    "will definitely overrun",
    "will not overrun",
    "definitely will overrun",
    "guaranteed to overrun",
    "guaranteed not to overrun",
    "has been performed",
    "has been completed",
]

SYSTEM_INSTRUCTION = """You write a short executive summary for an infrastructure project \
monitoring platform, answering four questions in order: (1) What is happening? (current health), \
(2) What is likely to happen? (the ML prediction, described as a forward-looking estimate, never \
a confirmed outcome), (3) Why? (top risk drivers), (4) What should be reviewed? (recommended \
monitoring actions).

Rules:
  - Use ONLY the structured facts given below - never invent a number, date, driver, or \
recommendation not present in them.
  - 3-6 plain sentences, neutral factual tone.
  - Never claim the project "will definitely overrun" or "will definitely not overrun".
  - Never claim a monitoring action "has been performed" - these are recommendations only.
  - If a section's data is not provided below, do not discuss it.
"""


@dataclass(frozen=True)
class NarrativeResult:
    text: str
    source: str  # "LLM" | "DETERMINISTIC_FALLBACK"
    model: str | None


def _deterministic_summary(
    project_name: str,
    health: HealthVector | None,
    prediction: PredictionResult | None,
    diagnosis: DiagnosisResult | None,
    intervention: InterventionResult | None,
) -> str:
    parts = [f"Analysis for {project_name}."]
    if health is not None:
        parts.append(f"Current health is {health.overall_health}.")
    if prediction is not None:
        parts.append(
            f"ML cost-overrun risk is {prediction.risk_level} "
            f"({prediction.probability * 100:.1f}% probability - a forward-looking estimate, "
            "not a confirmed outcome)."
        )
    if diagnosis is not None and diagnosis.drivers:
        top = diagnosis.drivers[0]
        parts.append(f"The top risk driver is: {top.driver} (severity {top.severity}).")
    if intervention is not None and intervention.recommendations:
        parts.append(f"Recommended: {intervention.recommendations[0].action}")
    return " ".join(parts)


def _format_context(
    project_name: str,
    health: HealthVector | None,
    prediction: PredictionResult | None,
    history: HistoryResult | None,
    diagnosis: DiagnosisResult | None,
    intervention: InterventionResult | None,
) -> str:
    lines = [f"Project: {project_name}"]

    if health is not None:
        lines.append(
            f"Current health: {health.overall_health} (progress gap {health.progress_gap}, "
            f"divergence {health.expenditure_progress_divergence}, trend {health.recent_trend.label})"
        )
    if prediction is not None:
        lines.append(
            f"ML cost-overrun prediction: {prediction.risk_level} risk, "
            f"{prediction.probability * 100:.1f}% probability (forward-looking, not confirmed)"
        )
    if history is not None and history.major_changes:
        lines.append("Key changes: " + "; ".join(c.description for c in history.major_changes[-5:]))
    if diagnosis is not None and diagnosis.drivers:
        lines.append(
            "Top risk drivers: "
            + "; ".join(f"{d.rank}. {d.driver} ({d.severity})" for d in diagnosis.drivers[:5])
        )
    if intervention is not None and intervention.recommendations:
        lines.append(
            "Recommended monitoring actions: "
            + "; ".join(r.action for r in intervention.recommendations[:5])
        )

    return "\n".join(lines)


def _violates_guardrail(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in FORBIDDEN_PHRASES)


def summarize_report(
    *,
    api_key: str | None,
    model: str,
    project_name: str,
    health: HealthVector | None,
    prediction: PredictionResult | None,
    history: HistoryResult | None = None,
    diagnosis: DiagnosisResult | None = None,
    intervention: InterventionResult | None = None,
) -> NarrativeResult:
    fallback_text = _deterministic_summary(project_name, health, prediction, diagnosis, intervention)

    if not api_key:
        return NarrativeResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None)

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        context = _format_context(project_name, health, prediction, history, diagnosis, intervention)
        response = client.models.generate_content(
            model=model,
            contents=context,
            config={"system_instruction": SYSTEM_INSTRUCTION, "temperature": 0.2},
        )
        text = (response.text or "").strip()
    except Exception:  # noqa: BLE001 - any LLM failure must degrade gracefully, never raise
        return NarrativeResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None)

    if not text or _violates_guardrail(text):
        return NarrativeResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None)

    return NarrativeResult(text=text, source="LLM", model=model)
