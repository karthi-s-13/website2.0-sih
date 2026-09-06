"""Intervention Agent orchestration (Phase 10, spec section 25): answers
"What should the monitoring authority look at next?" by running Phase 9's
Risk Diagnosis, then deterministically mapping every driver to a
review/verification/monitoring/information-request action (`mapping.py`) -
never an autonomous administrative decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.services.diagnosis.service import DiagnosisResult, diagnose_project
from app.services.intervention.mapping import (
    MONITORING,
    MONITORING_TRIGGER_LEVELS,
    OVERALL_RISK_TO_MONITORING_LEVEL,
    action_for_driver,
    assert_not_administrative_decision,
)


@dataclass(frozen=True)
class Recommendation:
    priority: str
    action_type: str
    action: str
    reason: str
    evidence_ids: list[str]
    review_area: str
    driver: str
    monitoring_level: str


@dataclass(frozen=True)
class InterventionResult:
    project_id: str
    project_name: str
    as_of_date: date
    overall_risk: str
    suggested_monitoring_level: str
    recommendations: list[Recommendation]
    # The full Phase 9 diagnosis this was computed from - already available
    # internally, exposed here so callers (the Phase 11 Coordinator/
    # Reporting) never need to re-run diagnose_project a second time just
    # to get drivers/evidence/risk_score.
    diagnosis: DiagnosisResult


def _recommendation_for_driver(driver, monitoring_level: str) -> Recommendation:
    template = action_for_driver(driver.driver_key, driver.driver)
    reason = f"{driver.driver} (severity {driver.severity})."
    assert_not_administrative_decision(template.action)
    assert_not_administrative_decision(reason)
    return Recommendation(
        priority=driver.severity,
        action_type=template.action_type,
        action=template.action,
        reason=reason,
        evidence_ids=list(driver.evidence_ids),
        review_area=template.review_area,
        driver=driver.driver,
        monitoring_level=monitoring_level,
    )


def _overall_monitoring_recommendation(
    diagnosis: DiagnosisResult, monitoring_level: str
) -> Recommendation | None:
    if diagnosis.overall_risk not in MONITORING_TRIGGER_LEVELS:
        return None
    evidence_ids = list(dict.fromkeys(eid for d in diagnosis.drivers for eid in d.evidence_ids))
    action = "Increase monitoring frequency and reporting cadence for this project."
    reason = (
        f"Overall project risk is {diagnosis.overall_risk}"
        + (f" (risk score {diagnosis.risk_score:.1f})." if diagnosis.risk_score is not None else ".")
    )
    assert_not_administrative_decision(action)
    assert_not_administrative_decision(reason)
    return Recommendation(
        priority=diagnosis.overall_risk,
        action_type=MONITORING,
        action=action,
        reason=reason,
        evidence_ids=evidence_ids,
        review_area="Monitoring Level",
        driver="",
        monitoring_level=monitoring_level,
    )


def recommend_interventions(
    session: Session,
    project_id: str,
    as_of_date: date | None = None,
    include_web: bool = True,
) -> InterventionResult:
    diagnosis = diagnose_project(session, project_id, as_of_date=as_of_date, include_web=include_web)

    monitoring_level = OVERALL_RISK_TO_MONITORING_LEVEL.get(diagnosis.overall_risk, "NORMAL")

    recommendations = [_recommendation_for_driver(d, monitoring_level) for d in diagnosis.drivers]

    overall_monitoring = _overall_monitoring_recommendation(diagnosis, monitoring_level)
    if overall_monitoring is not None:
        recommendations.append(overall_monitoring)

    return InterventionResult(
        project_id=diagnosis.project_id,
        project_name=diagnosis.project_name,
        as_of_date=diagnosis.as_of_date,
        overall_risk=diagnosis.overall_risk,
        suggested_monitoring_level=monitoring_level,
        recommendations=recommendations,
        diagnosis=diagnosis,
    )
