import pytest

from app.services.intervention.mapping import (
    ALL_ACTION_TYPES,
    COST_PROGRESS_REVIEW,
    IMPLEMENTATION_REVIEW,
    INFORMATION_REQUEST,
    MILESTONE_REVIEW,
    OVERALL_RISK_TO_MONITORING_LEVEL,
    REVIEW,
    VERIFICATION,
    AdministrativeDecisionGuardrailError,
    action_for_driver,
    assert_not_administrative_decision,
)

KNOWN_DRIVER_KEYS = [
    "HIGH_ML_RISK",
    "SCHEDULE_BEHIND",
    "EXPENDITURE_AHEAD",
    "DATA_QUALITY_CONCERN",
    "STAGNANT_TREND",
    "EXPENDITURE_ACCELERATION",
    "SUDDEN_PROGRESS_DECLINE",
    "MILESTONE_SLIPPAGE",
]


@pytest.mark.parametrize("driver_key", KNOWN_DRIVER_KEYS)
def test_every_known_driver_key_maps_to_a_controlled_action_type(driver_key: str) -> None:
    template = action_for_driver(driver_key, "some label")
    assert template.action_type in ALL_ACTION_TYPES
    assert template.action
    assert template.review_area


def test_schedule_behind_maps_to_milestone_review() -> None:
    template = action_for_driver("SCHEDULE_BEHIND", "Schedule progress gap")
    assert template.action_type == MILESTONE_REVIEW


def test_expenditure_ahead_maps_to_cost_progress_review() -> None:
    template = action_for_driver("EXPENDITURE_AHEAD", "Progress-expenditure divergence")
    assert template.action_type == COST_PROGRESS_REVIEW
    assert "expenditure" in template.action.lower()


def test_data_quality_concern_maps_to_information_request() -> None:
    template = action_for_driver("DATA_QUALITY_CONCERN", "Data quality anomalies in reported figures")
    assert template.action_type == INFORMATION_REQUEST


def test_stagnant_trend_maps_to_implementation_review() -> None:
    template = action_for_driver("STAGNANT_TREND", "Progress stagnation")
    assert template.action_type == IMPLEMENTATION_REVIEW


def test_sudden_progress_decline_maps_to_verification() -> None:
    template = action_for_driver("SUDDEN_PROGRESS_DECLINE", "Sudden decline in reported progress")
    assert template.action_type == VERIFICATION


def test_external_constraint_maps_to_verification_with_topic() -> None:
    template = action_for_driver("EXTERNAL_CONSTRAINT:land acquisition", "External constraint: land acquisition")
    assert template.action_type == VERIFICATION
    assert "land acquisition" in template.action


def test_unknown_driver_key_falls_back_to_generic_review() -> None:
    template = action_for_driver("SOME_FUTURE_KEY", "Some future concern")
    assert template.action_type == REVIEW
    assert "Some future concern" in template.action


def test_monitoring_level_covers_every_overall_risk_value() -> None:
    for level in ["LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL", "DATA_NOT_AVAILABLE"]:
        assert level in OVERALL_RISK_TO_MONITORING_LEVEL
        assert OVERALL_RISK_TO_MONITORING_LEVEL[level] in {"NORMAL", "ENHANCED", "PRIORITY", "CRITICAL"}


def test_guardrail_allows_review_language() -> None:
    assert_not_administrative_decision("Review expenditure against physical achievement.")
    assert_not_administrative_decision("Verify the externally reported land acquisition issue.")


def test_guardrail_blocks_administrative_decision_language() -> None:
    with pytest.raises(AdministrativeDecisionGuardrailError):
        assert_not_administrative_decision("Terminate the contract with the contractor.")


def test_guardrail_blocks_performed_claim() -> None:
    with pytest.raises(AdministrativeDecisionGuardrailError):
        assert_not_administrative_decision("The corrective action has been performed.")


def test_all_action_map_templates_pass_guardrail() -> None:
    for driver_key in KNOWN_DRIVER_KEYS:
        template = action_for_driver(driver_key, "label")
        assert_not_administrative_decision(template.action)  # must not raise
