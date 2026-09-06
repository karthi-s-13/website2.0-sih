"""LLM narrative synthesis for the Project History Agent (Phase 6).

This module has exactly one job: turn already-computed, deterministic
evidence (timeline.py) into a short human-readable `current_state` narrative
answering the user's question. It never computes facts, trends, or
predictions itself - those come in as arguments, already finished.

Graceful degradation (SRS section 24): if no API key is configured, the
Gemini call fails, or the model's output violates the output guardrail
(asserts a definite overrun/no-overrun outcome), a deterministic template
summary is used instead and the response says so explicitly. The agent must
never be blocked on the LLM being unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.history.timeline import MajorChange, RiskSignal, TimelineEntry

FORBIDDEN_PHRASES = [
    "will definitely not overrun",
    "will definitely overrun",
    "will not overrun",
    "definitely will overrun",
    "guaranteed to overrun",
    "guaranteed not to overrun",
]

SYSTEM_INSTRUCTION = """You are the Project History Agent for an infrastructure project monitoring \
platform. You answer the question "What happened to this project?" using ONLY the structured \
evidence provided below - never invent facts, dates, numbers, or events not present in it.

The evidence is pre-classified into three kinds; keep this distinction visible in your answer \
where relevant:
  - OBSERVED_FACT: directly recorded data or a plain diff between two recorded values.
  - INFERRED_TREND: a deterministic pattern/threshold judgment (health tier, stagnation, \
non-monotonic flag) - not a raw fact.
  - MODEL_PREDICTION: the ML model's own output - a forward-looking probability, not a fact.

Rules:
  - Write 3-5 plain sentences, chronological where relevant, in a neutral factual tone.
  - Never claim the project "will definitely overrun" or "will definitely not overrun" - the ML \
probability is a risk estimate, not a confirmed outcome.
  - If the evidence says no revised cost is recorded, say exactly that - do not imply the absence \
of a revised cost means the project is safe.
  - Do not use any number, date, or agency/state name that is not present in the evidence.
"""


@dataclass(frozen=True)
class SummaryResult:
    text: str
    source: str  # "LLM" | "DETERMINISTIC_FALLBACK"
    model: str | None


def _format_evidence(
    project_name: str,
    question: str,
    timeline: list[TimelineEntry],
    major_changes: list[MajorChange],
    risk_signals: list[RiskSignal],
    latest_health: dict,
) -> str:
    lines = [f"Project: {project_name}", f"Question: {question}", ""]

    lines.append("Latest health (INFERRED_TREND / deterministic):")
    for key, value in latest_health.items():
        lines.append(f"  - {key}: {value}")
    lines.append("")

    lines.append("Recent timeline (OBSERVED_FACT unless noted, most recent last):")
    for entry in timeline[-8:]:
        lines.append(f"  - [{entry.source_type}] {entry.month.isoformat()}: {entry.description}")
    lines.append("")

    if major_changes:
        lines.append("Major changes (OBSERVED_FACT):")
        for change in major_changes:
            lines.append(f"  - {change.month.isoformat()}: {change.description}")
        lines.append("")

    if risk_signals:
        lines.append("Risk signals:")
        for signal in risk_signals:
            lines.append(f"  - [{signal.source_type}] {signal.month.isoformat()}: {signal.description}")
        lines.append("")

    return "\n".join(lines)


def deterministic_fallback_summary(
    project_name: str,
    timeline: list[TimelineEntry],
    major_changes: list[MajorChange],
    risk_signals: list[RiskSignal],
) -> str:
    """A plain, template-based summary requiring no LLM at all - used both as
    the true fallback and to keep tests hermetic."""
    if not timeline:
        return f"No observation history is available for {project_name}."

    first, latest = timeline[0], timeline[-1]
    parts = [
        f"{project_name} has {len(timeline)} recorded timeline entries from "
        f"{first.month.isoformat()} to {latest.month.isoformat()}.",
        f"Most recent observation ({latest.month.isoformat()}): {latest.description}",
    ]
    if major_changes:
        parts.append(
            f"{len(major_changes)} major change(s) recorded, most recently: "
            f"{major_changes[-1].description}"
        )
    model_signals = [s for s in risk_signals if s.source_type == "MODEL_PREDICTION"]
    if model_signals:
        parts.append(model_signals[-1].description)
    return " ".join(parts)


def _violates_guardrail(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in FORBIDDEN_PHRASES)


def summarize_current_state(
    *,
    api_key: str | None,
    model: str,
    project_name: str,
    question: str,
    timeline: list[TimelineEntry],
    major_changes: list[MajorChange],
    risk_signals: list[RiskSignal],
    latest_health: dict,
) -> SummaryResult:
    fallback_text = deterministic_fallback_summary(project_name, timeline, major_changes, risk_signals)

    if not api_key:
        return SummaryResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None)

    try:
        from app.services.llm.groq_client import generate_text

        evidence = _format_evidence(
            project_name, question, timeline, major_changes, risk_signals, latest_health
        )
        text = generate_text(
            api_key=api_key, model=model, system_instruction=SYSTEM_INSTRUCTION, contents=evidence, temperature=0.2
        )
    except Exception:  # noqa: BLE001 - any LLM failure must degrade gracefully, never raise
        return SummaryResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None)

    if not text or _violates_guardrail(text):
        return SummaryResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None)

    return SummaryResult(text=text, source="LLM", model=model)
