"""Trigger gate for the Web Intelligence Agent (Phase 8).

Web search is never run on every request (spec section 96.5, "Uncontrolled
Web Search" anti-pattern - use targeted queries and budgets). It only runs
when at least one of these holds:

    - risk is high: overall_health or the ML risk_level is HIGH or CRITICAL
    - the user explicitly asked for it (`force`)
    - a future caller (the Phase 9 Risk Diagnosis Agent) needs it to verify a
      diagnosis (`for_diagnosis`) - accepted here, not wired to anything yet
"""

from __future__ import annotations

from dataclasses import dataclass

HIGH_RISK_HEALTH_LEVELS = {"HIGH", "CRITICAL"}
HIGH_RISK_ML_LEVELS = {"HIGH", "CRITICAL"}


@dataclass(frozen=True)
class TriggerDecision:
    triggered: bool
    reason: str


def should_trigger(
    *,
    overall_health: str | None,
    ml_risk_level: str | None,
    force: bool = False,
    for_diagnosis: bool = False,
) -> TriggerDecision:
    if force:
        return TriggerDecision(True, "Explicit user request (force=true).")
    if for_diagnosis:
        return TriggerDecision(True, "Required to verify a risk diagnosis.")
    if overall_health in HIGH_RISK_HEALTH_LEVELS:
        return TriggerDecision(True, f"Project health is {overall_health}.")
    if ml_risk_level in HIGH_RISK_ML_LEVELS:
        return TriggerDecision(True, f"ML cost-overrun risk level is {ml_risk_level}.")
    return TriggerDecision(
        False,
        "Risk is not currently high and no explicit request was made - web search skipped.",
    )
