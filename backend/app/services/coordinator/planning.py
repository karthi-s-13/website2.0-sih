"""Planning + Risk-Triggered Expansion (spec sections 7, 29-31).

The spec's 12 named stages (Data/History/Health/Prediction/Anomaly/Review/
Web/Evidence/Risk/Diagnosis/Intervention/Reporting) don't map 1:1 onto 12
separate service calls: Phase 9's `diagnose_project` already internally
runs Health + Prediction + Anomaly + Review + Web + Evidence Fusion + Risk
Fusion + Driver Diagnosis in one call, and Phase 10's `recommend_
interventions` already internally calls `diagnose_project` again. Planning
here in terms of the actual distinct calls (`DIAGNOSIS` and `INTERVENTION`
each being one bundled call) avoids silently duplicating every one of those
calls - see `stages.py` for what each call name actually does.
"""

from __future__ import annotations

from app.services.coordinator.intent import (
    ANOMALY_ANALYSIS,
    COMPLETE_PROJECT_ANALYSIS,
    COST_RISK,
    INTERVENTION,
    MONTHLY_CHANGE,
    PROJECT_HEALTH,
    PROJECT_HISTORY,
    PROJECT_LOOKUP,
    REPORT_GENERATION,
    REVIEW_REPORT_QUERY,
    RISK_ANALYSIS,
    TIME_RISK,
    WEB_INTELLIGENCE,
)
from app.services.web.trigger import HIGH_RISK_HEALTH_LEVELS, HIGH_RISK_ML_LEVELS

PROJECT = "PROJECT"
HISTORY = "HISTORY"
HEALTH = "HEALTH"
PREDICTION = "PREDICTION"
ANOMALY = "ANOMALY"
REVIEW = "REVIEW"
WEB = "WEB"
DIAGNOSIS = "DIAGNOSIS"
INTERVENTION_CALL = "INTERVENTION"

FULL_PLAN = [PROJECT, HISTORY, INTERVENTION_CALL]

# Matches the user's spec examples exactly:
#   Simple query ("What is the cost risk?")  -> Data, Prediction, Reporting
#   Health query                              -> Data, Health, Reporting
#   Full analysis                             -> Data, History, Health, Prediction,
#                                                 Anomaly, Review, Web, Evidence, Risk,
#                                                 Diagnosis, Intervention, Reporting
INTENT_PLAN: dict[str, list[str]] = {
    COST_RISK: [PROJECT, PREDICTION],
    TIME_RISK: [PROJECT, PREDICTION],
    PROJECT_HEALTH: [PROJECT, HEALTH],
    PROJECT_LOOKUP: [PROJECT],
    PROJECT_HISTORY: [PROJECT, HISTORY],
    MONTHLY_CHANGE: [PROJECT, HISTORY],
    ANOMALY_ANALYSIS: [PROJECT, ANOMALY],
    REVIEW_REPORT_QUERY: [PROJECT, REVIEW],
    WEB_INTELLIGENCE: [PROJECT, WEB],
    RISK_ANALYSIS: [PROJECT, HISTORY, DIAGNOSIS],
    INTERVENTION: [PROJECT, HISTORY, INTERVENTION_CALL],
    COMPLETE_PROJECT_ANALYSIS: FULL_PLAN,
    REPORT_GENERATION: FULL_PLAN,
}


def plan_for_intent(intent: str) -> list[str]:
    return list(INTENT_PLAN.get(intent, FULL_PLAN))


def should_expand(*, health_overall: str | None, ml_risk_level: str | None) -> bool:
    """Risk-triggered expansion (spec section 30): IF prediction is HIGH OR
    anomaly is HIGH OR health is CRITICAL THEN expand to deep analysis.
    Anomaly severity can only ever trigger this from within a plan that
    already computed anomalies (i.e. already the full plan) - so it isn't
    part of this narrow-plan check; a signal that was never computed can't
    trigger anything, never fabricated.
    """
    if health_overall == "CRITICAL":
        return True
    if ml_risk_level in HIGH_RISK_ML_LEVELS:
        return True
    return False


def expand_plan(plan: list[str]) -> list[str]:
    expanded = list(plan)
    for stage in FULL_PLAN:
        if stage not in expanded:
            expanded.append(stage)
    return expanded


__all__ = [
    "PROJECT",
    "HISTORY",
    "HEALTH",
    "PREDICTION",
    "ANOMALY",
    "REVIEW",
    "WEB",
    "DIAGNOSIS",
    "INTERVENTION_CALL",
    "FULL_PLAN",
    "INTENT_PLAN",
    "plan_for_intent",
    "should_expand",
    "expand_plan",
    "HIGH_RISK_HEALTH_LEVELS",
    "HIGH_RISK_ML_LEVELS",
]
