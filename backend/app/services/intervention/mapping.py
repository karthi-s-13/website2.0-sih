"""Deterministic Driver Classification -> Action Mapping -> Responsible
Review Area (spec section 25 workflow). No LLM - a plain, auditable lookup
table from a Phase 9 driver's stable `driver_key` to one of the seven
action types the user's spec names, so the agent can never invent an
action outside that controlled vocabulary.

Every action type is a *review, verification, monitoring, or information
request* - never an executed administrative act (approve/reject/withhold
funds/terminate a contract/etc.). This is enforced two ways: structurally
(the action templates below are the only thing this module can emit) and
defensively (`assert_not_administrative_decision`, a forbidden-phrase
guardrail checked by both the unit tests and `service.py`, mirroring the
guardrail shape already used in `history/llm.py` and `rag/answer.py`) -
matching spec section 25's explicit rule: "It should not issue autonomous
administrative decisions," and FR-027: "The agent shall not claim that an
action has been performed unless an authorized tool confirms it."
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.diagnosis.drivers import EXTERNAL_CONSTRAINT_KEY_PREFIX

REVIEW = "REVIEW"
VERIFICATION = "VERIFICATION"
MONITORING = "MONITORING"
INFORMATION_REQUEST = "INFORMATION_REQUEST"
MILESTONE_REVIEW = "MILESTONE_REVIEW"
COST_PROGRESS_REVIEW = "COST_PROGRESS_REVIEW"
IMPLEMENTATION_REVIEW = "IMPLEMENTATION_REVIEW"

ALL_ACTION_TYPES = [
    REVIEW,
    VERIFICATION,
    MONITORING,
    INFORMATION_REQUEST,
    MILESTONE_REVIEW,
    COST_PROGRESS_REVIEW,
    IMPLEMENTATION_REVIEW,
]

# Phrases that would cross the line from "look into this" to "an
# administrative decision was made" - never allowed in an action/reason
# string. Same guardrail shape as history/llm.py's FORBIDDEN_PHRASES.
FORBIDDEN_PHRASES = [
    "terminate the contract",
    "cancel the project",
    "withhold payment",
    "approve the revised cost",
    "reject the revised cost",
    "blacklist the contractor",
    "has been performed",
    "has been completed",
]


class AdministrativeDecisionGuardrailError(ValueError):
    pass


def assert_not_administrative_decision(text: str) -> None:
    lowered = text.lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in lowered:
            raise AdministrativeDecisionGuardrailError(
                f'action/reason text crosses into an administrative decision: "{phrase}"'
            )


@dataclass(frozen=True)
class ActionTemplate:
    action_type: str
    action: str
    review_area: str


ACTION_MAP: dict[str, ActionTemplate] = {
    "HIGH_ML_RISK": ActionTemplate(
        REVIEW,
        "Conduct a comprehensive project review in light of the elevated ML-predicted cost-overrun risk.",
        "Overall Project Review",
    ),
    "SCHEDULE_BEHIND": ActionTemplate(
        MILESTONE_REVIEW,
        "Review project milestones and schedule status against the approved timeline.",
        "Schedule & Milestones",
    ),
    "EXPENDITURE_AHEAD": ActionTemplate(
        COST_PROGRESS_REVIEW,
        "Review expenditure against physical achievement.",
        "Cost-Progress Reconciliation",
    ),
    "DATA_QUALITY_CONCERN": ActionTemplate(
        INFORMATION_REQUEST,
        "Request corrected or updated monthly figures from the implementing agency to resolve the "
        "data quality issue.",
        "Data Quality",
    ),
    "STAGNANT_TREND": ActionTemplate(
        IMPLEMENTATION_REVIEW,
        "Conduct an on-ground implementation review to identify the cause of progress stagnation.",
        "Implementation Status",
    ),
    "EXPENDITURE_ACCELERATION": ActionTemplate(
        COST_PROGRESS_REVIEW,
        "Review the recent expenditure surge against physical progress achieved.",
        "Cost-Progress Reconciliation",
    ),
    "SUDDEN_PROGRESS_DECLINE": ActionTemplate(
        VERIFICATION,
        "Verify the reported progress figures for the affected month with the implementing agency.",
        "Data Verification",
    ),
    "MILESTONE_SLIPPAGE": ActionTemplate(
        MILESTONE_REVIEW,
        "Review delayed milestones and revised completion timelines.",
        "Schedule & Milestones",
    ),
}

# Monitoring level suggestion (FR-028): NORMAL | ENHANCED | PRIORITY | CRITICAL.
OVERALL_RISK_TO_MONITORING_LEVEL: dict[str, str] = {
    "LOW": "NORMAL",
    "MODERATE": "ENHANCED",
    "ELEVATED": "ENHANCED",
    "HIGH": "PRIORITY",
    "CRITICAL": "CRITICAL",
    "DATA_NOT_AVAILABLE": "NORMAL",
}
MONITORING_TRIGGER_LEVELS = {"MODERATE", "ELEVATED", "HIGH", "CRITICAL"}


def action_for_driver(driver_key: str, driver_label: str) -> ActionTemplate:
    if driver_key.startswith(EXTERNAL_CONSTRAINT_KEY_PREFIX):
        topic = driver_key[len(EXTERNAL_CONSTRAINT_KEY_PREFIX) :]
        return ActionTemplate(
            VERIFICATION,
            f"Verify the externally reported {topic} issue with the implementing agency.",
            "External Evidence Verification",
        )
    if driver_key in ACTION_MAP:
        return ACTION_MAP[driver_key]
    # Unknown future driver key - still a safe, generic review action rather
    # than silently dropping the driver or guessing at something specific.
    return ActionTemplate(REVIEW, f"Review the reported concern: {driver_label}.", "General Review")
