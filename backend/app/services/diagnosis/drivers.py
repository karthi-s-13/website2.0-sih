"""Deterministic risk-driver identification (spec section 24 Risk Diagnosis
Agent, SRS FR-026). No LLM - every driver is a plain threshold rule over
already-computed Phase 3/4/8/9 outputs, and every driver's `evidence_ids` is
built strictly from the fused evidence pool (`app.services.evidence.fusion`)
so a driver can never be emitted without a traceable source.

Reuses `DRIVER_TOPIC_MAP` from `app.services.web.query_planner` (a pure data
constant, not the query-planning logic) as the single source of truth for
which web/review topics support which driver - the same table Phase 8 used
to decide which topics to search for in the first place, closing the loop
between "why we searched" and "what that search supports".
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.anomaly.formulas import (
    EXPENDITURE_ACCELERATION,
    EXPENDITURE_PROGRESS_DIVERGENCE,
    PROGRESS_STAGNATION,
    SCHEDULE_DETERIORATION,
    SUDDEN_PROGRESS_DECLINE,
)
from app.services.anomaly.service import AnomalyResult
from app.services.evidence.fusion import (
    FusedEvidence,
    OFFICIAL_EXTERNAL_SOURCE,
    REVIEW_REPORT,
    SECONDARY_SOURCE,
)
from app.services.health.formulas import DIVERGENCE_THRESHOLDS, SCHEDULE_SHORTFALL_THRESHOLDS, HealthVector
from app.services.web.query_planner import DRIVER_TOPIC_MAP

SEVERITY_RANK = {
    "NORMAL": 0,
    "LOW": 0,
    "WATCH": 1,
    "MODERATE": 1,
    "ELEVATED": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

TOPICS_FOR_CATEGORY: dict[str, list[str]] = dict(DRIVER_TOPIC_MAP)

EXTERNAL_RELEVANCE_THRESHOLD = 0.6
EXTERNAL_QUALITY_ALLOWED = {"HIGH", "MEDIUM"}


EXTERNAL_CONSTRAINT_KEY_PREFIX = "EXTERNAL_CONSTRAINT:"


@dataclass(frozen=True)
class Driver:
    rank: int
    driver: str
    severity: str
    evidence_ids: list[str]
    # A stable machine key (e.g. "SCHEDULE_BEHIND", or "EXTERNAL_CONSTRAINT:<topic>")
    # distinct from the human-readable `driver` label - lets downstream
    # consumers (Phase 10's Intervention Agent) branch reliably instead of
    # string-matching the label text.
    driver_key: str


def _tier_for(value: float, thresholds: list[tuple[float, str]]) -> str | None:
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return None


def _by_source_label(evidence: list[FusedEvidence], *labels: str) -> list[FusedEvidence]:
    return [e for e in evidence if e.source_label in labels]


def _by_topic(evidence: list[FusedEvidence], topics: list[str]) -> list[FusedEvidence]:
    web = [
        e
        for e in evidence
        if e.category in {OFFICIAL_EXTERNAL_SOURCE, SECONDARY_SOURCE} and e.topic in topics
    ]
    review = [
        e
        for e in evidence
        if e.category == REVIEW_REPORT and any(topic in e.description.lower() for topic in topics)
    ]
    return web + review


def _candidate(
    key: str,
    label: str,
    severity: str | None,
    core_evidence: list[FusedEvidence],
    all_evidence: list[FusedEvidence],
) -> tuple[str, str, str, list[str]] | None:
    if severity is None or not core_evidence:
        return None
    topics = TOPICS_FOR_CATEGORY.get(key, [])
    supporting = core_evidence + _by_topic(all_evidence, topics)
    evidence_ids = list(dict.fromkeys(e.evidence_id for e in supporting))
    return key, label, severity, evidence_ids


def _high_ml_risk(health: HealthVector, prediction, evidence: list[FusedEvidence]):
    if prediction is None or prediction.risk_level == "LOW":
        return None
    core = _by_source_label(evidence, f"ml_prediction:{prediction.model_version}")
    return _candidate("HIGH_ML_RISK", "High ML-predicted cost-overrun risk", prediction.risk_level, core, evidence)


def _schedule_behind(health: HealthVector, evidence: list[FusedEvidence]):
    if health.progress_gap is None or health.progress_gap >= 0:
        return None
    severity = _tier_for(-health.progress_gap, SCHEDULE_SHORTFALL_THRESHOLDS)
    core = _by_source_label(evidence, "health:progress_gap", f"anomaly:{SCHEDULE_DETERIORATION}")
    core += [e for e in evidence if e.source_label.startswith("project_events:COMPLETION_DATE_REVISED")]
    return _candidate("SCHEDULE_BEHIND", "Schedule progress gap", severity, core, evidence)


def _expenditure_ahead(health: HealthVector, evidence: list[FusedEvidence]):
    if health.expenditure_progress_divergence is None:
        return None
    severity = _tier_for(health.expenditure_progress_divergence, DIVERGENCE_THRESHOLDS)
    core = _by_source_label(
        evidence, "health:expenditure_progress_divergence", f"anomaly:{EXPENDITURE_PROGRESS_DIVERGENCE}"
    )
    core += [e for e in evidence if e.source_label.startswith("project_events:COST_REVISED")]
    return _candidate("EXPENDITURE_AHEAD", "Progress-expenditure divergence", severity, core, evidence)


def _data_quality_concern(evidence: list[FusedEvidence]):
    dq_items = [e for e in evidence if e.source_label.startswith("data_quality_issues:")]
    if not dq_items:
        return None
    mapped = {"ERROR": "HIGH", "WARNING": "MODERATE"}
    severities = [mapped.get(e.severity or "", None) for e in dq_items]
    severities = [s for s in severities if s]
    if not severities:
        return None
    severity = max(severities, key=lambda s: SEVERITY_RANK[s])
    return _candidate("DATA_QUALITY_CONCERN", "Data quality anomalies in reported figures", severity, dq_items, evidence)


def _stagnant_trend(health: HealthVector, evidence: list[FusedEvidence]):
    core = _by_source_label(evidence, f"anomaly:{PROGRESS_STAGNATION}")
    if health.recent_trend.label == "STAGNANT":
        core += _by_source_label(evidence, "health:recent_trend")
    if not core:
        return None
    severity = next((e.severity for e in core if e.source_label == f"anomaly:{PROGRESS_STAGNATION}"), "HIGH")
    return _candidate("STAGNANT_TREND", "Progress stagnation", severity, core, evidence)


def _anomaly_only_driver(anomaly_type: str, label: str, evidence: list[FusedEvidence]):
    core = _by_source_label(evidence, f"anomaly:{anomaly_type}")
    if not core:
        return None
    severity = core[0].severity
    return _candidate(anomaly_type, label, severity, core, evidence)


def _milestone_slippage(evidence: list[FusedEvidence]):
    core = _by_source_label(evidence, "health:milestone")
    if not core:
        return None
    severity = core[0].severity
    return _candidate("MILESTONE_SLIPPAGE", "Milestone slippage", severity, core, evidence)


def _external_constraints(evidence: list[FusedEvidence], covered_topics: set[str]):
    candidates: dict[str, list[FusedEvidence]] = {}
    for e in evidence:
        if e.category not in {OFFICIAL_EXTERNAL_SOURCE, SECONDARY_SOURCE}:
            continue
        if e.topic in covered_topics:
            continue
        if e.confidence < EXTERNAL_RELEVANCE_THRESHOLD:
            continue
        candidates.setdefault(e.topic or "unspecified", []).append(e)

    results = []
    for topic, items in candidates.items():
        best_quality_is_high = any(e.category == OFFICIAL_EXTERNAL_SOURCE for e in items)
        severity = "HIGH" if best_quality_is_high else "MODERATE"
        evidence_ids = [e.evidence_id for e in items]
        key = f"{EXTERNAL_CONSTRAINT_KEY_PREFIX}{topic}"
        results.append((key, f"External constraint: {topic}", severity, evidence_ids))
    return results


def identify_drivers(
    health: HealthVector,
    prediction,
    anomaly_result: AnomalyResult,
    evidence: list[FusedEvidence],
) -> list[Driver]:
    core_candidates = [
        _high_ml_risk(health, prediction, evidence),
        _schedule_behind(health, evidence),
        _expenditure_ahead(health, evidence),
        _data_quality_concern(evidence),
        _stagnant_trend(health, evidence),
        _anomaly_only_driver(EXPENDITURE_ACCELERATION, "Unusual expenditure acceleration", evidence),
        _anomaly_only_driver(SUDDEN_PROGRESS_DECLINE, "Sudden decline in reported progress", evidence),
        _milestone_slippage(evidence),
    ]
    core_candidates = [c for c in core_candidates if c is not None]

    covered_topics: set[str] = set()
    for key, _label, _severity, _ids in core_candidates:
        covered_topics.update(TOPICS_FOR_CATEGORY.get(key, []))
    external = _external_constraints(evidence, covered_topics)

    named_candidates = list(core_candidates) + external
    named_candidates.sort(key=lambda c: SEVERITY_RANK.get(c[2], 0), reverse=True)

    return [
        Driver(rank=i + 1, driver=label, severity=severity, evidence_ids=evidence_ids, driver_key=key)
        for i, (key, label, severity, evidence_ids) in enumerate(named_candidates)
    ]
