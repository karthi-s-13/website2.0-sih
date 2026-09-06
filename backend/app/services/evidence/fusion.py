"""Evidence Fusion (Phase 9, spec section 22 "Evidence Agent"): normalizes
every intelligence source built in Phases 1-8 into one pool of `FusedEvidence`
items, each tagged with **exactly one** of the six categories the user's
Phase 9 spec names - never mixed, so a diagnosis driver can never present an
unverified web claim as if it were an official project fact (SRS FR-020).

    PAIMANA_STRUCTURED_DATA    raw project_events / current observation facts
    ANALYTICAL_INFERENCE       Health (Phase 4) tiers + Anomaly (new) findings
                                + non-monotonic data-quality flags (same
                                classification History/Phase 6 already gives
                                these - flagging "non-monotonic" required a
                                rule, not a raw field read)
    MODEL_INFERENCE            the ML prediction (Phase 3)
    REVIEW_REPORT              Phase 7 review-report RAG citations
    OFFICIAL_EXTERNAL_SOURCE   Phase 8 web evidence, trust tier 1-2
    SECONDARY_SOURCE           Phase 8 web evidence, trust tier 3-5

Evidence IDs are deterministic (sha256 of stable identifying parts) for
sources that aren't independently persisted (events/DQ/health/anomaly/ML) -
reproducible, not a new DB row, same precedent Phase 4/6 already set. Web
evidence reuses its real, already-persisted `evidence_id` from Phase 8's
`web_evidence` table; review evidence gets a stable id derived from its
(document, page) citation.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.services.anomaly.service import AnomalyResult
from app.services.health.formulas import DIVERGENCE_THRESHOLDS, SCHEDULE_SHORTFALL_THRESHOLDS, HealthVector
from app.services.history.timeline import DQ_RISK_ISSUE_TYPES
from app.services.rag.service import EvidenceResult
from app.services.web.service import WebIntelligenceResult

PAIMANA_STRUCTURED_DATA = "PAIMANA_STRUCTURED_DATA"
ANALYTICAL_INFERENCE = "ANALYTICAL_INFERENCE"
MODEL_INFERENCE = "MODEL_INFERENCE"
REVIEW_REPORT = "REVIEW_REPORT"
OFFICIAL_EXTERNAL_SOURCE = "OFFICIAL_EXTERNAL_SOURCE"
SECONDARY_SOURCE = "SECONDARY_SOURCE"

OFFICIAL_TRUST_TIERS = {"TIER_1", "TIER_2"}

# The indexed "review reports" are national sector-aggregate bulletins that
# rarely name an individual project (see app/services/rag/answer.py) - these
# generic words recur in almost every project name and in that boilerplate,
# so they can't distinguish "this citation is actually about this project"
# from "this citation is generic infrastructure-sector text".
_GENERIC_PROJECT_NAME_TERMS = {
    "project", "projects", "system", "systems", "strengthening", "integration",
    "generation", "power", "grid", "corporation", "corp", "india", "limited",
    "spv", "name", "transmission", "augmentation", "development", "construction",
    "national", "scheme", "phase", "works", "road", "roads", "railway",
    "railways", "renewable", "energy", "infrastructure", "sector", "ministry",
    "district", "state",
}


def _distinctive_project_terms(project_name: str, agency_code: str | None) -> list[str]:
    """Terms specific enough that their presence in a review-report excerpt
    means the excerpt is actually about this project, not just generic
    sector boilerplate that happens to share common infrastructure vocabulary."""
    words = re.findall(r"[A-Za-z]{5,}", project_name)
    terms = [w.lower() for w in words if w.lower() not in _GENERIC_PROJECT_NAME_TERMS]
    if agency_code:
        terms.append(agency_code.lower())
    return terms


@dataclass(frozen=True)
class FusedEvidence:
    evidence_id: str
    category: str
    description: str
    confidence: float
    source_label: str
    topic: str | None = None
    severity: str | None = None
    month: date | None = None


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _tier_for(value: float, thresholds: list[tuple[float, str]]) -> str | None:
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return None


def _structured_data_evidence(project_id: str, events: list[Any], as_of: date) -> list[FusedEvidence]:
    items = []
    for ev in events:
        if ev.event_type == "PROJECT_FIRST_OBSERVED" or ev.event_month > as_of:
            continue
        items.append(
            FusedEvidence(
                evidence_id=_stable_id("evt", project_id, ev.event_type, ev.event_month.isoformat()),
                category=PAIMANA_STRUCTURED_DATA,
                description=ev.description,
                confidence=1.0,
                source_label=f"project_events:{ev.event_type}",
                month=ev.event_month,
            )
        )
    return items


def _health_evidence(project_id: str, health: HealthVector) -> list[FusedEvidence]:
    items = []
    if health.progress_gap is not None:
        tier = _tier_for(-health.progress_gap, SCHEDULE_SHORTFALL_THRESHOLDS) if health.progress_gap < 0 else None
        items.append(
            FusedEvidence(
                evidence_id=_stable_id("health-gap", project_id, health.snapshot_month.isoformat()),
                category=ANALYTICAL_INFERENCE,
                description=(
                    f"Physical progress is {health.progress_gap:+.1f} points vs expected schedule "
                    f"as of {health.snapshot_month.isoformat()}."
                ),
                confidence=1.0,
                source_label="health:progress_gap",
                severity=tier,
                month=health.snapshot_month,
            )
        )
    if health.expenditure_progress_divergence is not None:
        tier = _tier_for(health.expenditure_progress_divergence, DIVERGENCE_THRESHOLDS)
        items.append(
            FusedEvidence(
                evidence_id=_stable_id("health-div", project_id, health.snapshot_month.isoformat()),
                category=ANALYTICAL_INFERENCE,
                description=(
                    f"Expenditure-progress divergence is {health.expenditure_progress_divergence:+.1f} "
                    f"points as of {health.snapshot_month.isoformat()}."
                ),
                confidence=1.0,
                source_label="health:expenditure_progress_divergence",
                severity=tier,
                month=health.snapshot_month,
            )
        )
    if health.recent_trend.label not in {None, "DATA_NOT_AVAILABLE"}:
        items.append(
            FusedEvidence(
                evidence_id=_stable_id("health-trend", project_id, health.snapshot_month.isoformat()),
                category=ANALYTICAL_INFERENCE,
                description=f"Recent trend is {health.recent_trend.label}.",
                confidence=1.0,
                source_label="health:recent_trend",
                severity="HIGH" if health.recent_trend.label == "STAGNANT" else None,
                month=health.snapshot_month,
            )
        )
    return items


def _milestone_evidence(project_id: str, health: HealthVector) -> list[FusedEvidence]:
    m = health.milestone_health
    if m.status in {"NOT_AVAILABLE", "GOOD"}:
        return []  # dormant for this dataset (Phase 4: no milestone fields in the source data)
    return [
        FusedEvidence(
            evidence_id=_stable_id("milestone", project_id, health.snapshot_month.isoformat()),
            category=ANALYTICAL_INFERENCE,
            description=f"{m.delayed} of {m.total} milestones are delayed ({m.status}).",
            confidence=1.0,
            source_label="health:milestone",
            severity="HIGH" if m.status == "POOR" else "MODERATE",
            month=health.snapshot_month,
        )
    ]


def _anomaly_evidence(project_id: str, anomaly_result: AnomalyResult) -> list[FusedEvidence]:
    return [
        FusedEvidence(
            evidence_id=_stable_id("anom", project_id, a.anomaly_type, a.month.isoformat()),
            category=ANALYTICAL_INFERENCE,
            description=a.description,
            confidence=a.score,
            source_label=f"anomaly:{a.anomaly_type}",
            severity=a.severity,
            month=a.month,
        )
        for a in anomaly_result.anomalies
    ]


def _dq_evidence(project_id: str, dq_issues: list[Any]) -> list[FusedEvidence]:
    items = []
    for issue in dq_issues:
        if issue.issue_type not in DQ_RISK_ISSUE_TYPES:
            continue
        items.append(
            FusedEvidence(
                evidence_id=_stable_id("dq", project_id, issue.issue_type, str(issue.id)),
                category=ANALYTICAL_INFERENCE,
                description=(
                    f"{issue.field} did not increase as expected (recorded value: {issue.original_value})."
                ),
                confidence=0.8,
                source_label=f"data_quality_issues:{issue.issue_type}",
                severity=issue.severity,
            )
        )
    return items


def _model_evidence(project_id: str, prediction: Any, as_of: date) -> list[FusedEvidence]:
    if prediction is None:
        return []
    return [
        FusedEvidence(
            evidence_id=_stable_id("ml", project_id, as_of.isoformat(), prediction.model_version),
            category=MODEL_INFERENCE,
            description=(
                f"Model {prediction.model_version} estimates a {prediction.probability * 100:.1f}% "
                f"probability of future cost overrun ({prediction.risk_level} risk level). This is a "
                "forward-looking risk estimate, not a confirmed outcome."
            ),
            confidence=1.0,
            source_label=f"ml_prediction:{prediction.model_version}",
            severity=prediction.risk_level,
            month=as_of,
        )
    ]


def _review_evidence(
    project_id: str, review: EvidenceResult | None, distinctive_terms: list[str]
) -> list[FusedEvidence]:
    if review is None or not review.evidence_found:
        return []
    items = []
    for c in review.citations:
        # Never present a generic national-sector bulletin excerpt as if it
        # were evidence about this specific project (SRS FR-020's "no false
        # connection" rule) - only excerpts that actually name the project or
        # its agency qualify.
        if distinctive_terms and not any(term in c.excerpt.lower() for term in distinctive_terms):
            continue
        items.append(
            FusedEvidence(
                evidence_id=_stable_id("rev", project_id, c.document_name, str(c.page)),
                category=REVIEW_REPORT,
                description=c.excerpt[:300],
                confidence=min(max(c.score, 0.0), 1.0),
                source_label=f"{c.document_name} p.{c.page}",
            )
        )
    return items


def _web_evidence(web: WebIntelligenceResult | None) -> list[FusedEvidence]:
    if web is None or not web.triggered:
        return []
    items = []
    for item in web.evidence:
        category = OFFICIAL_EXTERNAL_SOURCE if item.trust_tier in OFFICIAL_TRUST_TIERS else SECONDARY_SOURCE
        items.append(
            FusedEvidence(
                evidence_id=item.evidence_id,
                category=category,
                description=item.finding,
                confidence=item.project_relevance,
                source_label=item.source,
                topic=item.topic,
                month=item.publication_date,
            )
        )
    return items


def fuse_evidence(
    *,
    project_id: str,
    project_name: str = "",
    agency_code: str | None = None,
    as_of: date,
    health: HealthVector,
    anomaly_result: AnomalyResult,
    events: list[Any],
    dq_issues: list[Any],
    prediction: Any,
    review: EvidenceResult | None,
    web: WebIntelligenceResult | None,
) -> list[FusedEvidence]:
    distinctive_terms = _distinctive_project_terms(project_name, agency_code)
    return [
        *_structured_data_evidence(project_id, events, as_of),
        *_health_evidence(project_id, health),
        *_milestone_evidence(project_id, health),
        *_anomaly_evidence(project_id, anomaly_result),
        *_dq_evidence(project_id, dq_issues),
        *_model_evidence(project_id, prediction, as_of),
        *_review_evidence(project_id, review, distinctive_terms),
        *_web_evidence(web),
    ]
