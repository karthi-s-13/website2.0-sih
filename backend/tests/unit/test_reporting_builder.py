from datetime import date
from types import SimpleNamespace

from app.services.diagnosis.drivers import Driver
from app.services.diagnosis.service import DiagnosisResult
from app.services.evidence.fusion import ANALYTICAL_INFERENCE, FusedEvidence
from app.services.health.formulas import HealthVector, MilestoneHealth, RecentTrend
from app.services.intervention.service import InterventionResult, Recommendation
from app.services.reporting.builder import build_report

SNAPSHOT = date(2026, 7, 1)

HEALTH = HealthVector(
    snapshot_month=SNAPSHOT, overall_health="CRITICAL", cost_utilisation=80.0, schedule_utilisation=50.0,
    physical_progress=20.0, expected_progress=50.0, progress_gap=-30.0, expenditure_progress_divergence=60.0,
    recent_trend=RecentTrend(1.0, 5.0, 1.0, 5.0, 0, "DECLINING"),
    milestone_health=MilestoneHealth(status="NOT_AVAILABLE", total=0, completed=0, delayed=0),
    input_observation_count=6,
)

PREDICTION = SimpleNamespace(
    project_id="p1", prediction_date="2026-07-01", risk_type="cost_overrun", probability=0.9,
    risk_level="CRITICAL", model_version="m1", feature_version="features-v1", leakage_check="PASSED",
)

DRIVER = Driver(rank=1, driver="Progress-expenditure divergence", severity="CRITICAL", evidence_ids=["ev-1"], driver_key="EXPENDITURE_AHEAD")
EVIDENCE = FusedEvidence(
    evidence_id="ev-1", category=ANALYTICAL_INFERENCE, description="divergence high", confidence=1.0,
    source_label="health:expenditure_progress_divergence",
)
DIAGNOSIS = DiagnosisResult(
    project_id="p1", project_name="Test Project", as_of_date=SNAPSHOT, overall_risk="CRITICAL",
    risk_score=90.0, confidence=0.8, fusion_version="risk-fusion-v1", drivers=[DRIVER], evidence=[EVIDENCE],
)
RECOMMENDATION = Recommendation(
    priority="CRITICAL", action_type="COST_PROGRESS_REVIEW", action="Review expenditure against physical achievement.",
    reason="Progress-expenditure divergence (severity CRITICAL).", evidence_ids=["ev-1"],
    review_area="Cost-Progress Reconciliation", driver="Progress-expenditure divergence", monitoring_level="CRITICAL",
)
INTERVENTION = InterventionResult(
    project_id="p1", project_name="Test Project", as_of_date=SNAPSHOT, overall_risk="CRITICAL",
    suggested_monitoring_level="CRITICAL", recommendations=[RECOMMENDATION], diagnosis=DIAGNOSIS,
)


def test_build_report_with_nothing_computed() -> None:
    report = build_report(
        trace_id="t1", analysis_id="a1", project_id="p1", project_name="Test Project",
        as_of_date=SNAPSHOT, executive_summary="stub",
    )
    assert report.current_health is None
    assert report.cost_overrun_risk is None
    assert report.time_overrun_risk is None
    assert report.key_changes == []
    assert report.top_risk_drivers == []
    assert report.evidence == []
    assert report.recommended_monitoring_actions == []
    assert report.human_review_required is False


def test_build_report_with_health_only() -> None:
    report = build_report(
        trace_id="t1", analysis_id="a1", project_id="p1", project_name="Test Project",
        as_of_date=SNAPSHOT, executive_summary="stub", health=HEALTH,
    )
    assert report.current_health["overall_health"] == "CRITICAL"
    assert report.cost_overrun_risk is None


def test_build_report_time_overrun_always_not_available() -> None:
    report = build_report(
        trace_id="t1", analysis_id="a1", project_id="p1", project_name="Test Project",
        as_of_date=SNAPSHOT, executive_summary="stub", prediction=PREDICTION,
    )
    assert report.time_overrun_risk == {
        "status": "NOT_AVAILABLE",
        "reason": "No time-overrun prediction model is currently deployed.",
    }
    assert report.cost_overrun_risk["risk_level"] == "CRITICAL"


def test_build_report_critical_risk_requires_human_review() -> None:
    report = build_report(
        trace_id="t1", analysis_id="a1", project_id="p1", project_name="Test Project",
        as_of_date=SNAPSHOT, executive_summary="stub", diagnosis=DIAGNOSIS,
    )
    assert report.human_review_required is True
    assert "CRITICAL" in report.human_review_reason


def test_build_report_prediction_error_requires_human_review() -> None:
    report = build_report(
        trace_id="t1", analysis_id="a1", project_id="p1", project_name="Test Project",
        as_of_date=SNAPSHOT, executive_summary="stub", prediction_error=True,
    )
    assert report.human_review_required is True


def test_build_report_full_pipeline() -> None:
    report = build_report(
        trace_id="t1", analysis_id="a1", project_id="p1", project_name="Test Project",
        as_of_date=SNAPSHOT, executive_summary="stub", health=HEALTH, prediction=PREDICTION,
        diagnosis=DIAGNOSIS, intervention=INTERVENTION,
    )
    assert len(report.top_risk_drivers) == 1
    assert report.top_risk_drivers[0]["driver"] == "Progress-expenditure divergence"
    assert len(report.evidence) == 1
    assert len(report.recommended_monitoring_actions) == 1
    assert report.model_versions["ml_model_version"] == "m1"
    assert report.model_versions["risk_fusion_version"] == "risk-fusion-v1"
    assert report.confidence["diagnosis_confidence"] == 0.8
