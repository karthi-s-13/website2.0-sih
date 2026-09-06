from types import SimpleNamespace

from app.services.anomaly.formulas import Anomaly
from app.services.diagnosis.risk_fusion import RISK_FUSION_VERSION, fuse_risk
from app.services.evidence.fusion import OFFICIAL_EXTERNAL_SOURCE, SECONDARY_SOURCE, FusedEvidence
from app.services.health.formulas import HealthVector, MilestoneHealth, RecentTrend
from datetime import date

SNAPSHOT = date(2026, 7, 1)


def _health(progress_gap=None, divergence=None) -> HealthVector:
    return HealthVector(
        snapshot_month=SNAPSHOT,
        overall_health="NORMAL",
        cost_utilisation=20.0,
        schedule_utilisation=20.0,
        physical_progress=20.0,
        expected_progress=20.0,
        progress_gap=progress_gap,
        expenditure_progress_divergence=divergence,
        recent_trend=RecentTrend(1.0, 5.0, 1.0, 5.0, 0, "STABLE"),
        milestone_health=MilestoneHealth(status="NOT_AVAILABLE", total=0, completed=0, delayed=0),
        input_observation_count=3,
    )


def test_no_data_available_returns_data_not_available() -> None:
    result = fuse_risk(_health(), None, None, [])
    assert result.overall_risk == "DATA_NOT_AVAILABLE"
    assert result.risk_score is None
    assert result.confidence == 0.0
    assert result.fusion_version == RISK_FUSION_VERSION


def test_high_ml_probability_alone_drives_high_risk() -> None:
    prediction = SimpleNamespace(model_version="m1", probability=0.95, risk_level="CRITICAL")
    result = fuse_risk(_health(), prediction, None, [])
    assert result.risk_score == 95.0
    assert result.overall_risk == "CRITICAL"
    assert 0 < result.confidence <= 1.0


def test_low_ml_probability_alone_is_low_risk() -> None:
    prediction = SimpleNamespace(model_version="m1", probability=0.05, risk_level="LOW")
    result = fuse_risk(_health(), prediction, None, [])
    assert result.overall_risk == "LOW"


def test_empty_anomaly_list_is_available_evidence_of_normalcy() -> None:
    """An empty list (checked, found nothing) must count as available data,
    distinct from `None` (never checked) - it should count towards a LOWER
    risk score, not be excluded from the weighted average."""
    prediction = SimpleNamespace(model_version="m1", probability=0.5, risk_level="ELEVATED")
    without_anomaly_check = fuse_risk(_health(), prediction, None, [])
    with_clean_anomaly_check = fuse_risk(_health(), prediction, [], [])
    assert with_clean_anomaly_check.confidence > without_anomaly_check.confidence
    assert with_clean_anomaly_check.risk_score < without_anomaly_check.risk_score


def test_confidence_increases_with_more_available_dimensions() -> None:
    prediction = SimpleNamespace(model_version="m1", probability=0.5, risk_level="ELEVATED")
    only_ml = fuse_risk(_health(), prediction, [], [])
    with_schedule = fuse_risk(_health(progress_gap=-40.0), prediction, [], [])
    assert with_schedule.confidence > only_ml.confidence


def test_anomaly_severity_contributes_to_score() -> None:
    anomalies = [Anomaly("EXPENDITURE_ACCELERATION", "CRITICAL", 0.9, "spike", SNAPSHOT)]
    result = fuse_risk(_health(), None, anomalies, [])
    assert result.risk_score == 100.0
    assert result.overall_risk == "CRITICAL"


def test_official_external_evidence_scores_higher_than_secondary() -> None:
    official = [
        FusedEvidence(
            evidence_id="ev-1", category=OFFICIAL_EXTERNAL_SOURCE, description="d", confidence=1.0,
            source_label="pib.gov.in",
        )
    ]
    secondary = [
        FusedEvidence(
            evidence_id="ev-2", category=SECONDARY_SOURCE, description="d", confidence=1.0,
            source_label="blog.example.com",
        )
    ]
    official_result = fuse_risk(_health(), None, [], official)
    secondary_result = fuse_risk(_health(), None, [], secondary)
    assert official_result.risk_score > secondary_result.risk_score


def test_secondary_only_evidence_reduces_confidence() -> None:
    prediction = SimpleNamespace(model_version="m1", probability=0.5, risk_level="ELEVATED")
    secondary = [
        FusedEvidence(
            evidence_id="ev-2", category=SECONDARY_SOURCE, description="d", confidence=1.0,
            source_label="blog.example.com",
        )
    ]
    official = [
        FusedEvidence(
            evidence_id="ev-3", category=OFFICIAL_EXTERNAL_SOURCE, description="d", confidence=1.0,
            source_label="pib.gov.in",
        )
    ]
    with_secondary_only = fuse_risk(_health(), prediction, None, secondary)
    with_official = fuse_risk(_health(), prediction, None, official)
    # Both add the same extra dimension, but secondary-only evidence must be
    # discounted relative to official evidence (FR-020: never authoritative).
    assert with_secondary_only.confidence < with_official.confidence
    assert with_secondary_only.confidence == round((2 / 5) * 0.85, 4)


def test_risk_score_rounded_to_two_decimals() -> None:
    prediction = SimpleNamespace(model_version="m1", probability=0.333333, risk_level="MODERATE")
    result = fuse_risk(_health(), prediction, [], [])
    assert result.risk_score == round(result.risk_score, 2)
