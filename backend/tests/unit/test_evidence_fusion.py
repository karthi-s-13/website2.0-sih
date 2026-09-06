from datetime import date
from types import SimpleNamespace

from app.services.anomaly.formulas import Anomaly
from app.services.anomaly.service import AnomalyResult
from app.services.evidence.fusion import (
    ANALYTICAL_INFERENCE,
    MODEL_INFERENCE,
    OFFICIAL_EXTERNAL_SOURCE,
    PAIMANA_STRUCTURED_DATA,
    REVIEW_REPORT,
    SECONDARY_SOURCE,
    fuse_evidence,
)
from app.services.health.formulas import HealthVector, MilestoneHealth, RecentTrend
from app.services.rag.answer import AnswerResult, Citation
from app.services.rag.service import EvidenceResult
from app.services.web.service import WebEvidenceItem, WebIntelligenceResult

SNAPSHOT = date(2026, 7, 1)

HEALTH = HealthVector(
    snapshot_month=SNAPSHOT,
    overall_health="ELEVATED",
    cost_utilisation=33.2,
    schedule_utilisation=70.8,
    physical_progress=37.0,
    expected_progress=70.8,
    progress_gap=-33.8,
    expenditure_progress_divergence=-3.8,
    recent_trend=RecentTrend(1.0, 5.0, 1.0, 5.0, 0, "IMPROVING"),
    milestone_health=MilestoneHealth(status="NOT_AVAILABLE", total=0, completed=0, delayed=0),
    input_observation_count=6,
)

ANOMALY_RESULT = AnomalyResult(
    project_id="617069",
    snapshot_month=SNAPSHOT,
    anomalies=[
        Anomaly(
            anomaly_type="PROGRESS_STAGNATION",
            severity="HIGH",
            score=0.5,
            description="Physical progress has not changed for 3 consecutive observed months.",
            month=SNAPSHOT,
        )
    ],
    unavailable_types=["UNEXPECTED_MILESTONE_CHANGES"],
    input_observation_count=6,
)

EVENT = SimpleNamespace(
    event_type="COST_REVISED",
    event_month=date(2026, 6, 1),
    description="Revised cost changed from unrecorded to ₹466.00 Cr.",
)

DQ_ISSUE = SimpleNamespace(
    id=1,
    issue_type="NON_MONOTONIC_CUMULATIVE_EXPENDITURE",
    severity="WARNING",
    field="cumulative_expenditure_crore",
    original_value="12.0",
)

PREDICTION = SimpleNamespace(model_version="cost-overrun-lightgbm-2026", probability=0.72, risk_level="HIGH")

REVIEW = EvidenceResult(
    project_id="617069",
    project_name="Test Project",
    question="q",
    answer="stub",
    citations=[Citation(document_name="Report.pdf", page=5, excerpt="A funding delay was noted.", score=0.8)],
    summary_source="LLM",
    summary_model="gemini-3.6-flash",
    evidence_found=True,
    searched_at="2026-07-01T00:00:00Z",
)

WEB = WebIntelligenceResult(
    project_id="617069",
    project_name="Test Project",
    triggered=True,
    trigger_reason="force",
    topics_searched=["funding"],
    evidence=[
        WebEvidenceItem(
            evidence_id="ev-abc123",
            topic="funding",
            source="pib.gov.in",
            url="https://pib.gov.in/press",
            title="Funding update",
            publication_date=date(2026, 6, 15),
            date_confidence="VERIFIED",
            finding="A funding delay was officially confirmed.",
            project_relevance=0.9,
            trust_tier="TIER_1",
            source_quality="HIGH",
        ),
        WebEvidenceItem(
            evidence_id="ev-def456",
            topic="contractor dispute",
            source="randomblog.example.com",
            url="https://randomblog.example.com/post",
            title="Blog post",
            publication_date=None,
            date_confidence="UNVERIFIED",
            finding="A blog claims a contractor dispute.",
            project_relevance=0.4,
            trust_tier="TIER_4",
            source_quality="LOW",
        ),
    ],
    warnings=[],
    searched_at="2026-07-01T00:00:00Z",
)


def _fuse(**overrides):
    kwargs = dict(
        project_id="617069",
        as_of=SNAPSHOT,
        health=HEALTH,
        anomaly_result=ANOMALY_RESULT,
        events=[EVENT],
        dq_issues=[DQ_ISSUE],
        prediction=PREDICTION,
        review=REVIEW,
        web=WEB,
    )
    kwargs.update(overrides)
    return fuse_evidence(**kwargs)


def test_fuse_evidence_categorizes_every_source() -> None:
    items = _fuse()
    categories = {i.category for i in items}
    assert PAIMANA_STRUCTURED_DATA in categories
    assert ANALYTICAL_INFERENCE in categories
    assert MODEL_INFERENCE in categories
    assert REVIEW_REPORT in categories
    assert OFFICIAL_EXTERNAL_SOURCE in categories
    assert SECONDARY_SOURCE in categories


def test_web_evidence_split_by_trust_tier() -> None:
    items = _fuse()
    official = [i for i in items if i.category == OFFICIAL_EXTERNAL_SOURCE]
    secondary = [i for i in items if i.category == SECONDARY_SOURCE]
    assert any(i.evidence_id == "ev-abc123" for i in official)
    assert any(i.evidence_id == "ev-def456" for i in secondary)


def test_web_evidence_ids_are_reused_verbatim() -> None:
    items = _fuse()
    web_items = [i for i in items if i.category in {OFFICIAL_EXTERNAL_SOURCE, SECONDARY_SOURCE}]
    assert {i.evidence_id for i in web_items} == {"ev-abc123", "ev-def456"}


def test_evidence_ids_are_deterministic_across_calls() -> None:
    first = _fuse()
    second = _fuse()
    assert [i.evidence_id for i in first] == [i.evidence_id for i in second]


def test_no_ml_prediction_produces_no_model_inference_evidence() -> None:
    items = _fuse(prediction=None)
    assert not any(i.category == MODEL_INFERENCE for i in items)


def test_no_review_evidence_when_not_found() -> None:
    not_found = EvidenceResult(
        project_id="617069",
        project_name="Test Project",
        question="q",
        answer="not mentioned",
        citations=[],
        summary_source="DETERMINISTIC_FALLBACK",
        summary_model=None,
        evidence_found=False,
        searched_at="2026-07-01T00:00:00Z",
    )
    items = _fuse(review=not_found)
    assert not any(i.category == REVIEW_REPORT for i in items)


def test_no_web_evidence_when_not_triggered() -> None:
    not_triggered = WebIntelligenceResult(
        project_id="617069",
        project_name="Test Project",
        triggered=False,
        trigger_reason="not high risk",
        topics_searched=[],
        evidence=[],
        warnings=[],
        searched_at="2026-07-01T00:00:00Z",
    )
    items = _fuse(web=not_triggered)
    assert not any(i.category in {OFFICIAL_EXTERNAL_SOURCE, SECONDARY_SOURCE} for i in items)


def test_project_first_observed_event_excluded() -> None:
    first_observed = SimpleNamespace(
        event_type="PROJECT_FIRST_OBSERVED", event_month=date(2025, 1, 1), description="First observed."
    )
    items = _fuse(events=[first_observed])
    assert not any(i.category == PAIMANA_STRUCTURED_DATA for i in items)


def test_events_after_as_of_excluded() -> None:
    future_event = SimpleNamespace(
        event_type="COST_REVISED", event_month=date(2027, 1, 1), description="Future event."
    )
    items = _fuse(events=[future_event])
    assert not any(i.category == PAIMANA_STRUCTURED_DATA for i in items)
