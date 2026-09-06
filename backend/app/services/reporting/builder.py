"""Deterministic Reporting Agent assembly (spec section 26 required sections,
section 64's four-question decision-explanation format, section 65's example
final response). No LLM here - this module only assembles a `Report` from
whatever upstream results the Coordinator actually computed; `narrative.py`
is the one place an LLM writes anything, and only the executive summary
paragraph, grounded strictly in the fields this module already built.

Every field is `None` when its underlying stage never ran - never
backfilled, guessed, or defaulted to a "safe-looking" value.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.services.diagnosis.service import DiagnosisResult
from app.services.health.formulas import HealthVector
from app.services.history.service import HistoryResult
from app.services.intervention.service import InterventionResult
from app.services.prediction.service import PredictionResult
from app.services.rag.service import EvidenceResult
from app.services.web.service import WebIntelligenceResult

# Human escalation trigger (spec section 48): critical risk, model
# unavailable, or low data confidence.
LOW_CONFIDENCE_THRESHOLD = 0.4
TOP_DRIVERS_LIMIT = 5
TOP_EVIDENCE_LIMIT = 10


@dataclass(frozen=True)
class Report:
    trace_id: str
    analysis_id: str
    project_id: str
    project_name: str
    as_of_date: date
    executive_summary: str
    current_health: dict | None
    cost_overrun_risk: dict | None
    time_overrun_risk: dict | None
    key_changes: list[str]
    top_risk_drivers: list[dict]
    evidence: list[dict]
    recommended_monitoring_actions: list[dict]
    confidence: dict
    data_quality: dict
    model_versions: dict
    human_review_required: bool
    human_review_reason: str | None


def _current_health(health: HealthVector | None) -> dict | None:
    if health is None:
        return None
    return {
        "overall_health": health.overall_health,
        "cost_utilisation": health.cost_utilisation,
        "schedule_utilisation": health.schedule_utilisation,
        "physical_progress": health.physical_progress,
        "expected_progress": health.expected_progress,
        "progress_gap": health.progress_gap,
        "expenditure_progress_divergence": health.expenditure_progress_divergence,
        "recent_trend": health.recent_trend.label,
    }


def _cost_overrun_risk(prediction: PredictionResult | None) -> dict | None:
    if prediction is None:
        return None
    return {
        "probability": prediction.probability,
        "risk_level": prediction.risk_level,
        "model_version": prediction.model_version,
    }


def _time_overrun_risk(prediction: PredictionResult | None) -> dict | None:
    """No time-overrun model was ever built (Phase 3 built cost-overrun
    only) - reported honestly as unavailable, never fabricated, whenever a
    prediction was requested at all."""
    if prediction is None:
        return None
    return {
        "status": "NOT_AVAILABLE",
        "reason": "No time-overrun prediction model is currently deployed.",
    }


def _key_changes(history: HistoryResult | None) -> list[str]:
    if history is None:
        return []
    return [c.description for c in history.major_changes]


def _top_risk_drivers(diagnosis: DiagnosisResult | None) -> list[dict]:
    if diagnosis is None:
        return []
    return [
        {
            "rank": d.rank,
            "driver": d.driver,
            "severity": d.severity,
            "evidence_count": len(d.evidence_ids),
        }
        for d in diagnosis.drivers[:TOP_DRIVERS_LIMIT]
    ]


def _evidence(
    diagnosis: DiagnosisResult | None,
    review: EvidenceResult | None,
    web: WebIntelligenceResult | None,
) -> list[dict]:
    if diagnosis is not None:
        return [
            {
                "evidence_id": e.evidence_id,
                "category": e.category,
                "description": e.description,
                "confidence": e.confidence,
                "source": e.source_label,
            }
            for e in diagnosis.evidence[:TOP_EVIDENCE_LIMIT]
        ]
    items = []
    if review is not None and review.evidence_found:
        items.extend(
            {
                "evidence_id": f"{c.document_name}:{c.page}",
                "category": "REVIEW_REPORT",
                "description": c.excerpt,
                "confidence": c.score,
                "source": f"{c.document_name} p.{c.page}",
            }
            for c in review.citations
        )
    if web is not None and web.triggered:
        items.extend(
            {
                "evidence_id": e.evidence_id,
                "category": "OFFICIAL_EXTERNAL_SOURCE" if e.trust_tier in {"TIER_1", "TIER_2"} else "SECONDARY_SOURCE",
                "description": e.finding,
                "confidence": e.project_relevance,
                "source": e.source,
            }
            for e in web.evidence
        )
    return items[:TOP_EVIDENCE_LIMIT]


def _recommended_actions(intervention: InterventionResult | None) -> list[dict]:
    if intervention is None:
        return []
    return [
        {"priority": r.priority, "action": r.action, "action_type": r.action_type}
        for r in intervention.recommendations
    ]


def _confidence(diagnosis: DiagnosisResult | None) -> dict:
    if diagnosis is None:
        return {}
    return {"diagnosis_confidence": diagnosis.confidence}


def _data_quality(health: HealthVector | None) -> dict:
    if health is None:
        return {}
    return {"input_observation_count": health.input_observation_count}


def _model_versions(prediction: PredictionResult | None, diagnosis: DiagnosisResult | None) -> dict:
    versions: dict = {}
    if prediction is not None:
        versions["ml_model_version"] = prediction.model_version
        versions["feature_version"] = prediction.feature_version
    if diagnosis is not None:
        versions["risk_fusion_version"] = diagnosis.fusion_version
    return versions


def _human_review(
    overall_risk: str | None,
    prediction: PredictionResult | None,
    prediction_error: bool,
    diagnosis: DiagnosisResult | None,
) -> tuple[bool, str | None]:
    if overall_risk == "CRITICAL":
        return True, "Overall risk is CRITICAL."
    if prediction_error:
        return True, "The ML prediction model was unavailable for this analysis."
    if diagnosis is not None and diagnosis.confidence < LOW_CONFIDENCE_THRESHOLD:
        return True, f"Diagnosis confidence is low ({diagnosis.confidence:.2f})."
    return False, None


def build_report(
    *,
    trace_id: str,
    analysis_id: str,
    project_id: str,
    project_name: str,
    as_of_date: date,
    executive_summary: str,
    history: HistoryResult | None = None,
    health: HealthVector | None = None,
    prediction: PredictionResult | None = None,
    prediction_error: bool = False,
    review: EvidenceResult | None = None,
    web: WebIntelligenceResult | None = None,
    diagnosis: DiagnosisResult | None = None,
    intervention: InterventionResult | None = None,
) -> Report:
    overall_risk = diagnosis.overall_risk if diagnosis is not None else (intervention.overall_risk if intervention else None)
    human_review_required, human_review_reason = _human_review(overall_risk, prediction, prediction_error, diagnosis)

    return Report(
        trace_id=trace_id,
        analysis_id=analysis_id,
        project_id=project_id,
        project_name=project_name,
        as_of_date=as_of_date,
        executive_summary=executive_summary,
        current_health=_current_health(health),
        cost_overrun_risk=_cost_overrun_risk(prediction),
        time_overrun_risk=_time_overrun_risk(prediction),
        key_changes=_key_changes(history),
        top_risk_drivers=_top_risk_drivers(diagnosis),
        evidence=_evidence(diagnosis, review, web),
        recommended_monitoring_actions=_recommended_actions(intervention),
        confidence=_confidence(diagnosis),
        data_quality=_data_quality(health),
        model_versions=_model_versions(prediction, diagnosis),
        human_review_required=human_review_required,
        human_review_reason=human_review_reason,
    )
