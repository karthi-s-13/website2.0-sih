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

import re
from dataclasses import dataclass

from app.services.diagnosis.service import DiagnosisResult
from app.services.health.formulas import SCHEDULE_SHORTFALL_THRESHOLDS, HealthVector
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

SYSTEM_INSTRUCTION = """You are a senior infrastructure policy analyst writing an authoritative executive brief for government project monitoring (MoSPI / Cabinet Committee on Infrastructure standard).

Answer the core monitoring questions clearly and concisely:
1. Schedule & Completion Outlook: Is the project on track to finish on time? State physical progress vs target schedule clearly.
2. Financial & Cost Telemetry: Current health status, budget divergence, and ML cost overrun risk probability (described as a forward-looking risk estimate, never a confirmed outcome).
3. Root Causes & Risk Drivers: Top institutional, contractor, or milestone bottlenecks.
4. Action Directives: Specific recommended monitoring and mitigation steps.

Rules:
  - Use ONLY the structured facts given below - never invent a number, date, driver, or recommendation not present in them.
  - If a specific user question is given, begin your reply with one direct sentence answering that exact question, then use the four-part structure below to support it.
  - Authoritative, professional, government-grade executive tone.
  - Never claim the project "will definitely overrun" or "will definitely not overrun".
  - Never claim a monitoring action "has been performed" - these are recommendations only.
  - If a section's data is not provided below, do not discuss it.
"""

# Keyword fallback (mirrors coordinator/intent.py's pattern, same priority
# order - intervention/cause questions checked before the broader schedule
# pattern, since a question like "what interventions can reduce the delay"
# contains "delay" too and must not be misread as a plain schedule query)
# for when the LLM is unavailable (no key, quota exhausted, guardrail
# violation) - the deterministic summary must still visibly respond to what
# was actually asked, not just recite the same fixed brief every time
# regardless of which question prompted it.
_INTERVENTION_QUESTION_RE = re.compile(
    r"\brecommend|what should (we|i) do|next step|\bintervention|\bmitigat|\breduce\b|\bfix\b",
    re.I,
)
_RISK_DRIVER_QUESTION_RE = re.compile(
    r"\bwhy\b.*\brisk\b|risk driver|\bdiagnos|\bcause\b|\breason\b", re.I
)
_COST_QUESTION_RE = re.compile(r"\bcost.?overrun\b|\bcost risk\b|\bbudget\b|\boverrun\b", re.I)
_SCHEDULE_QUESTION_RE = re.compile(
    r"\bon time\b|\bon track\b|\bon schedule\b|finish(ed|ing)?\s+on\s+time|\bdelay(ed|s)?\b|"
    r"\bschedule risk\b|\btime.?overrun\b|\bcompletion\b",
    re.I,
)


def _schedule_tier(gap: float | None) -> str | None:
    """The same WATCH/ELEVATED/HIGH/CRITICAL tier used everywhere else this
    project's schedule shortfall is reported (evidence, risk drivers) - the
    narrative must never invent its own, differently-worded severity scale
    that could contradict those figures in the same response."""
    if gap is None or gap >= 0:
        return None
    shortfall = -gap
    for threshold, label in SCHEDULE_SHORTFALL_THRESHOLDS:
        if shortfall >= threshold:
            return label
    return None


def _direct_schedule_answer(health: HealthVector | None) -> str | None:
    if health is None or health.progress_gap is None:
        return None
    gap = health.progress_gap
    tier = _schedule_tier(gap)
    if tier is not None:
        verdict = f"is NOT currently on track to finish on schedule (severity: {tier})"
    elif gap < 0:
        verdict = "is running slightly behind its planned schedule"
    else:
        verdict = "is currently on track against its planned schedule"
    trend_label = health.recent_trend.label if health.recent_trend else None
    trend_note = ""
    if trend_label not in (None, "DATA_NOT_AVAILABLE"):
        trend_note = f" The recent trend is {trend_label.replace('_', ' ').lower()}."
    return (
        f"Direct answer: this project {verdict} - physical progress is {gap:+.1f} points "
        f"versus the expected schedule as of {health.snapshot_month.isoformat()}.{trend_note}"
    )


def _direct_intervention_answer(intervention: InterventionResult | None) -> str | None:
    if intervention is None or not intervention.recommendations:
        return None
    top = intervention.recommendations[0]
    action = top.action.rstrip(".")
    action = action[0].lower() + action[1:] if action else ""
    driver_note = f", targeting the primary driver '{top.driver}'" if top.driver else ""
    return (
        f"Direct answer: the highest-priority recommended action is to {action}{driver_note} "
        f"(priority {top.priority}). Suggested monitoring level: {intervention.suggested_monitoring_level}."
    )


def _direct_risk_driver_answer(diagnosis: DiagnosisResult | None) -> str | None:
    if diagnosis is None or not diagnosis.drivers:
        return None
    top = diagnosis.drivers[0]
    return (
        f"Direct answer: overall project risk is {diagnosis.overall_risk}, driven primarily by "
        f"{top.driver} (severity {top.severity})."
    )


def _direct_cost_answer(prediction: PredictionResult | None) -> str | None:
    if prediction is None:
        return None
    return (
        f"Direct answer: the ML model estimates a {prediction.probability * 100:.1f}% probability of "
        f"future cost overrun ({prediction.risk_level} risk level) - a forward-looking estimate, not a "
        "confirmed outcome."
    )


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
    question: str | None = None,
) -> str:
    parts = []

    # 0. Directly answer the specific question asked, when we can recognize it -
    # never just recite the same fixed brief regardless of what was asked.
    # Checked in the same priority order as coordinator/intent.py's own
    # keyword fallback, so an intervention/cause question (which may also
    # contain schedule words like "delay") is never misread as a plain
    # schedule query.
    direct_answer = None
    if question:
        if _INTERVENTION_QUESTION_RE.search(question):
            direct_answer = _direct_intervention_answer(intervention)
        elif _RISK_DRIVER_QUESTION_RE.search(question):
            direct_answer = _direct_risk_driver_answer(diagnosis)
        elif _COST_QUESTION_RE.search(question):
            direct_answer = _direct_cost_answer(prediction)
        elif _SCHEDULE_QUESTION_RE.search(question):
            direct_answer = _direct_schedule_answer(health)
    if direct_answer is not None:
        parts.append(direct_answer)

    # 1. Project Status & Schedule Completion Outlook
    if health is not None:
        gap = health.progress_gap
        trend = health.recent_trend.label.replace("_", " ").title() if health.recent_trend else "Stable"
        tier = _schedule_tier(gap)
        if tier is not None:
            completion_status = f"Project schedule status is {tier}, with a physical progress deficit of {abs(gap):.1f} percentage points against the planned schedule."
        elif gap is not None and gap < 0:
            completion_status = f"Project is slightly behind schedule, with a physical progress gap of {abs(gap):.1f} percentage points."
        else:
            completion_status = "Project is on track relative to its target physical progress schedule."

        supporting_detail = (
            f"Overall monitoring health is classified as {health.overall_health}. "
            f"Physical completion is recorded at {health.physical_progress:.1f}% (expected baseline: {health.expected_progress:.1f}%), "
            f"with recent progress trajectory marked as {trend}."
        )
        if parts:
            # A direct answer already opened the reply and stated the same
            # verdict - don't repeat it, just add the supporting figures.
            parts.append(supporting_detail)
        else:
            parts.append(f"Executive Analysis for {project_name}: {completion_status} {supporting_detail}")
    elif not parts:
        parts.append(f"Executive Analysis for {project_name}.")

    # 2. Forward-looking ML Overrun Forecast
    if prediction is not None:
        parts.append(
            f"The ML predictive engine projects a {prediction.probability * 100:.1f}% probability of future cost overrun ({prediction.risk_level} risk level). "
            "This indicates that while cost escalation is currently bounded, physical milestone recovery remains the critical operational priority."
        )

    # 3. Key Risk Drivers
    if diagnosis is not None and diagnosis.drivers:
        drivers_summary = ", ".join(f"{d.driver} ({d.severity})" for d in diagnosis.drivers[:3])
        parts.append(f"Primary risk drivers identified from review telemetry and audit matrices include: {drivers_summary}.")

    # 4. Actionable Directives
    if intervention is not None and intervention.recommendations:
        top_actions = "; ".join(f"{r.action}" for r in intervention.recommendations[:2])
        parts.append(f"Recommended institutional interventions: {top_actions}.")

    return " ".join(parts)


def _format_context(
    project_name: str,
    health: HealthVector | None,
    prediction: PredictionResult | None,
    history: HistoryResult | None,
    diagnosis: DiagnosisResult | None,
    intervention: InterventionResult | None,
    question: str | None = None,
) -> str:
    lines = [f"Project: {project_name}"]
    if question:
        lines.append(f"User question: {question}")

    if health is not None:
        gap = health.progress_gap
        tier = _schedule_tier(gap)
        if tier is not None:
            schedule_status = f"{tier} (behind schedule)"
        elif gap is not None and gap < 0:
            schedule_status = "slightly behind schedule"
        else:
            schedule_status = "on track"
        gap_str = f"{gap:+.1f}" if gap is not None else "unavailable"
        divergence = health.expenditure_progress_divergence
        divergence_str = f"{divergence:+.1f}" if divergence is not None else "unavailable"
        lines.append(
            f"Current health: {health.overall_health} (progress gap {gap_str} points, "
            f"schedule status: {schedule_status}, divergence {divergence_str} points, "
            f"trend {health.recent_trend.label})"
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


# Matches "on track"/"on schedule" unless immediately preceded by a
# negation ("NOT on track", "isn't on schedule") - a fixed-width lookbehind
# is enough since both negations are 4 characters.
_UNNEGATED_ON_TRACK_RE = re.compile(r"(?<!not )(?<!n't )\bon (track|schedule)\b", re.I)


def _violates_guardrail(text: str, health: HealthVector | None = None) -> bool:
    lowered = text.lower()
    if any(phrase in lowered for phrase in FORBIDDEN_PHRASES):
        return True
    # An LLM claiming the project is "on track" while the project's own
    # computed schedule tier says otherwise is a hallucination that
    # contradicts the grounding data it was given - never let generated
    # prose override the deterministic facts (SRS FR-020).
    if health is not None and _schedule_tier(health.progress_gap) is not None:
        if _UNNEGATED_ON_TRACK_RE.search(lowered):
            return True
    return False


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
    question: str | None = None,
) -> NarrativeResult:
    fallback_text = _deterministic_summary(project_name, health, prediction, diagnosis, intervention, question)

    if not api_key:
        return NarrativeResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None)

    try:
        from app.services.llm.groq_client import generate_text

        context = _format_context(project_name, health, prediction, history, diagnosis, intervention, question)
        text = generate_text(
            api_key=api_key, model=model, system_instruction=SYSTEM_INSTRUCTION, contents=context, temperature=0.2
        )
    except Exception:  # noqa: BLE001 - any LLM failure must degrade gracefully, never raise
        return NarrativeResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None)

    if not text or _violates_guardrail(text, health):
        return NarrativeResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None)

    return NarrativeResult(text=text, source="LLM", model=model)
