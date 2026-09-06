from datetime import date
from types import SimpleNamespace

from app.services.anomaly.formulas import Anomaly
from app.services.anomaly.service import AnomalyResult
from app.services.diagnosis.drivers import identify_drivers
from app.services.evidence.fusion import (
    ANALYTICAL_INFERENCE,
    MODEL_INFERENCE,
    OFFICIAL_EXTERNAL_SOURCE,
    FusedEvidence,
)
from app.services.health.formulas import HealthVector, MilestoneHealth, RecentTrend

SNAPSHOT = date(2026, 7, 1)

NORMAL_HEALTH = HealthVector(
    snapshot_month=SNAPSHOT,
    overall_health="NORMAL",
    cost_utilisation=20.0,
    schedule_utilisation=20.0,
    physical_progress=20.0,
    expected_progress=20.0,
    progress_gap=0.0,
    expenditure_progress_divergence=0.0,
    recent_trend=RecentTrend(1.0, 5.0, 1.0, 5.0, 0, "IMPROVING"),
    milestone_health=MilestoneHealth(status="NOT_AVAILABLE", total=0, completed=0, delayed=0),
    input_observation_count=3,
)

EMPTY_ANOMALY_RESULT = AnomalyResult(
    project_id="p1", snapshot_month=SNAPSHOT, anomalies=[], unavailable_types=[], input_observation_count=3
)


def test_no_drivers_when_everything_normal() -> None:
    drivers = identify_drivers(NORMAL_HEALTH, None, EMPTY_ANOMALY_RESULT, [])
    assert drivers == []


def test_high_ml_risk_driver_with_evidence() -> None:
    prediction = SimpleNamespace(model_version="m1", probability=0.8, risk_level="HIGH")
    evidence = [
        FusedEvidence(
            evidence_id="ml-1",
            category=MODEL_INFERENCE,
            description="high risk",
            confidence=1.0,
            source_label="ml_prediction:m1",
        )
    ]
    drivers = identify_drivers(NORMAL_HEALTH, prediction, EMPTY_ANOMALY_RESULT, evidence)
    assert len(drivers) == 1
    assert drivers[0].driver == "High ML-predicted cost-overrun risk"
    assert drivers[0].severity == "HIGH"
    assert drivers[0].evidence_ids == ["ml-1"]


def test_low_ml_risk_produces_no_driver() -> None:
    prediction = SimpleNamespace(model_version="m1", probability=0.1, risk_level="LOW")
    evidence = [
        FusedEvidence(
            evidence_id="ml-1", category=MODEL_INFERENCE, description="low risk", confidence=1.0,
            source_label="ml_prediction:m1",
        )
    ]
    drivers = identify_drivers(NORMAL_HEALTH, prediction, EMPTY_ANOMALY_RESULT, evidence)
    assert drivers == []


def test_schedule_behind_driver() -> None:
    health = HealthVector(**{**NORMAL_HEALTH.__dict__, "progress_gap": -40.0})
    evidence = [
        FusedEvidence(
            evidence_id="health-gap-1", category=ANALYTICAL_INFERENCE, description="behind schedule",
            confidence=1.0, source_label="health:progress_gap", severity="HIGH",
        )
    ]
    drivers = identify_drivers(health, None, EMPTY_ANOMALY_RESULT, evidence)
    assert any(d.driver == "Schedule progress gap" for d in drivers)


def test_anomaly_only_driver_expenditure_acceleration() -> None:
    anomaly_result = AnomalyResult(
        project_id="p1",
        snapshot_month=SNAPSHOT,
        anomalies=[
            Anomaly(
                anomaly_type="EXPENDITURE_ACCELERATION",
                severity="CRITICAL",
                score=0.9,
                description="spike",
                month=SNAPSHOT,
            )
        ],
        unavailable_types=[],
        input_observation_count=5,
    )
    evidence = [
        FusedEvidence(
            evidence_id="anom-1", category=ANALYTICAL_INFERENCE, description="spike", confidence=0.9,
            source_label="anomaly:EXPENDITURE_ACCELERATION", severity="CRITICAL",
        )
    ]
    drivers = identify_drivers(NORMAL_HEALTH, None, anomaly_result, evidence)
    assert len(drivers) == 1
    assert drivers[0].driver == "Unusual expenditure acceleration"
    assert drivers[0].severity == "CRITICAL"


def test_external_constraint_for_uncovered_topic() -> None:
    evidence = [
        FusedEvidence(
            evidence_id="ev-1", category=OFFICIAL_EXTERNAL_SOURCE, description="local issue reported",
            confidence=0.9, source_label="pib.gov.in", topic="local issue",
        )
    ]
    drivers = identify_drivers(NORMAL_HEALTH, None, EMPTY_ANOMALY_RESULT, evidence)
    assert len(drivers) == 1
    assert drivers[0].driver == "External constraint: local issue"
    assert drivers[0].severity == "HIGH"
    assert drivers[0].evidence_ids == ["ev-1"]


def test_low_relevance_web_evidence_does_not_become_driver() -> None:
    evidence = [
        FusedEvidence(
            evidence_id="ev-1", category=OFFICIAL_EXTERNAL_SOURCE, description="weak match",
            confidence=0.2, source_label="pib.gov.in", topic="local issue",
        )
    ]
    drivers = identify_drivers(NORMAL_HEALTH, None, EMPTY_ANOMALY_RESULT, evidence)
    assert drivers == []


def test_web_evidence_attaches_to_covered_driver_instead_of_external() -> None:
    prediction = SimpleNamespace(model_version="m1", probability=0.8, risk_level="HIGH")
    evidence = [
        FusedEvidence(
            evidence_id="ml-1", category=MODEL_INFERENCE, description="high risk", confidence=1.0,
            source_label="ml_prediction:m1",
        ),
        FusedEvidence(
            evidence_id="ev-1", category=OFFICIAL_EXTERNAL_SOURCE, description="funding delay",
            confidence=0.9, source_label="pib.gov.in", topic="funding",
        ),
    ]
    drivers = identify_drivers(NORMAL_HEALTH, prediction, EMPTY_ANOMALY_RESULT, evidence)
    assert len(drivers) == 1  # not split into a separate "External constraint: funding" driver
    assert set(drivers[0].evidence_ids) == {"ml-1", "ev-1"}


def test_drivers_ranked_by_severity_descending() -> None:
    prediction = SimpleNamespace(model_version="m1", probability=0.35, risk_level="MODERATE")
    health = HealthVector(**{**NORMAL_HEALTH.__dict__, "progress_gap": -60.0})
    evidence = [
        FusedEvidence(
            evidence_id="ml-1", category=MODEL_INFERENCE, description="moderate risk", confidence=1.0,
            source_label="ml_prediction:m1",
        ),
        FusedEvidence(
            evidence_id="health-gap-1", category=ANALYTICAL_INFERENCE, description="way behind",
            confidence=1.0, source_label="health:progress_gap", severity="CRITICAL",
        ),
    ]
    drivers = identify_drivers(health, prediction, EMPTY_ANOMALY_RESULT, evidence)
    assert drivers[0].driver == "Schedule progress gap"  # CRITICAL ranks above MODERATE
    assert drivers[0].rank == 1
    assert drivers[1].rank == 2


def test_driver_key_is_stable_machine_id() -> None:
    prediction = SimpleNamespace(model_version="m1", probability=0.8, risk_level="HIGH")
    evidence = [
        FusedEvidence(
            evidence_id="ml-1", category=MODEL_INFERENCE, description="high risk", confidence=1.0,
            source_label="ml_prediction:m1",
        )
    ]
    drivers = identify_drivers(NORMAL_HEALTH, prediction, EMPTY_ANOMALY_RESULT, evidence)
    assert drivers[0].driver_key == "HIGH_ML_RISK"


def test_external_constraint_driver_key_carries_topic() -> None:
    evidence = [
        FusedEvidence(
            evidence_id="ev-1", category=OFFICIAL_EXTERNAL_SOURCE, description="local issue reported",
            confidence=0.9, source_label="pib.gov.in", topic="local issue",
        )
    ]
    drivers = identify_drivers(NORMAL_HEALTH, None, EMPTY_ANOMALY_RESULT, evidence)
    assert drivers[0].driver_key == "EXTERNAL_CONSTRAINT:local issue"


def test_data_quality_concern_severity_mapping() -> None:
    evidence = [
        FusedEvidence(
            evidence_id="dq-1", category=ANALYTICAL_INFERENCE, description="non-monotonic",
            confidence=0.8, source_label="data_quality_issues:NON_MONOTONIC_CUMULATIVE_EXPENDITURE",
            severity="ERROR",
        )
    ]
    drivers = identify_drivers(NORMAL_HEALTH, None, EMPTY_ANOMALY_RESULT, evidence)
    assert len(drivers) == 1
    assert drivers[0].driver == "Data quality anomalies in reported figures"
    assert drivers[0].severity == "HIGH"
