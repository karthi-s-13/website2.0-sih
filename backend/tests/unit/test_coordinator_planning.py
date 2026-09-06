from app.services.coordinator.intent import (
    ANOMALY_ANALYSIS,
    COMPLETE_PROJECT_ANALYSIS,
    COST_RISK,
    INTERVENTION,
    PROJECT_HEALTH,
    PROJECT_HISTORY,
    PROJECT_LOOKUP,
    REPORT_GENERATION,
    REVIEW_REPORT_QUERY,
    RISK_ANALYSIS,
    TIME_RISK,
    WEB_INTELLIGENCE,
)
from app.services.coordinator.planning import (
    DIAGNOSIS,
    FULL_PLAN,
    HEALTH,
    HISTORY,
    INTERVENTION_CALL,
    PREDICTION,
    PROJECT,
    expand_plan,
    plan_for_intent,
    should_expand,
)


def test_cost_risk_matches_simple_query_example() -> None:
    assert plan_for_intent(COST_RISK) == [PROJECT, PREDICTION]


def test_time_risk_includes_health_and_prediction() -> None:
    # No time-overrun ML model exists - HEALTH's progress-vs-schedule gap is
    # the only real signal available to answer a schedule question.
    assert plan_for_intent(TIME_RISK) == [PROJECT, HEALTH, PREDICTION]


def test_project_health_matches_health_query_example() -> None:
    assert plan_for_intent(PROJECT_HEALTH) == [PROJECT, HEALTH]


def test_project_lookup_is_minimal() -> None:
    assert plan_for_intent(PROJECT_LOOKUP) == [PROJECT]


def test_complete_project_analysis_matches_full_analysis_example() -> None:
    plan = plan_for_intent(COMPLETE_PROJECT_ANALYSIS)
    assert plan == [PROJECT, HISTORY, INTERVENTION_CALL]
    assert plan == FULL_PLAN


def test_report_generation_same_as_complete() -> None:
    assert plan_for_intent(REPORT_GENERATION) == plan_for_intent(COMPLETE_PROJECT_ANALYSIS)


def test_intervention_intent_includes_history_and_intervention() -> None:
    assert plan_for_intent(INTERVENTION) == [PROJECT, HISTORY, INTERVENTION_CALL]


def test_risk_analysis_uses_diagnosis_not_intervention() -> None:
    plan = plan_for_intent(RISK_ANALYSIS)
    assert DIAGNOSIS in plan
    assert INTERVENTION_CALL not in plan


def test_review_and_web_intents_are_narrow() -> None:
    assert plan_for_intent(REVIEW_REPORT_QUERY) == [PROJECT, "REVIEW"]
    assert plan_for_intent(WEB_INTELLIGENCE) == [PROJECT, "WEB"]


def test_anomaly_intent_is_narrow() -> None:
    assert plan_for_intent(ANOMALY_ANALYSIS) == [PROJECT, "ANOMALY"]


def test_unknown_intent_falls_back_to_full_plan() -> None:
    assert plan_for_intent("SOME_UNKNOWN_INTENT") == FULL_PLAN


def test_project_history_is_narrow() -> None:
    assert plan_for_intent(PROJECT_HISTORY) == [PROJECT, HISTORY]


def test_should_expand_on_critical_health() -> None:
    assert should_expand(health_overall="CRITICAL", ml_risk_level=None) is True


def test_should_expand_on_high_ml_risk() -> None:
    assert should_expand(health_overall="NORMAL", ml_risk_level="HIGH") is True


def test_should_expand_on_critical_ml_risk() -> None:
    assert should_expand(health_overall=None, ml_risk_level="CRITICAL") is True


def test_should_not_expand_when_signals_are_normal() -> None:
    assert should_expand(health_overall="NORMAL", ml_risk_level="LOW") is False


def test_should_not_expand_when_nothing_was_computed() -> None:
    assert should_expand(health_overall=None, ml_risk_level=None) is False


def test_expand_plan_adds_missing_full_plan_stages() -> None:
    expanded = expand_plan([PROJECT, PREDICTION])
    assert expanded[: len([PROJECT, PREDICTION])] == [PROJECT, PREDICTION]
    for stage in FULL_PLAN:
        assert stage in expanded


def test_expand_plan_does_not_duplicate_existing_stages() -> None:
    expanded = expand_plan(FULL_PLAN)
    assert expanded == FULL_PLAN
