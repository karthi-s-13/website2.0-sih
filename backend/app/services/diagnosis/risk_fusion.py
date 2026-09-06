"""Deterministic Risk Fusion (spec section 23): "Risk Fusion should
preferably be implemented as a deterministic scoring service" - no LLM
anywhere in this module. A weighted combination of whichever risk
dimensions actually have data, each weight a named, versioned constant
(spec section 23's explicit requirement) so it can be retuned later against
evaluation data (Phase 14) without touching the logic.

`overall_risk`'s label reuses `prediction.risk.risk_level_for_probability`
directly (FR-025's 0-100 -> LOW/MODERATE/ELEVATED/HIGH/CRITICAL scale is
byte-for-byte the same scale already implemented there) rather than
inventing a second vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.anomaly.formulas import Anomaly
from app.services.evidence.fusion import OFFICIAL_EXTERNAL_SOURCE, SECONDARY_SOURCE, FusedEvidence
from app.services.health.formulas import DIVERGENCE_THRESHOLDS, SCHEDULE_SHORTFALL_THRESHOLDS, HealthVector
from app.services.prediction.risk import risk_level_for_probability

RISK_FUSION_VERSION = "risk-fusion-v1"

# Weights sum to 1.0 across all five dimensions; renormalized over whichever
# dimensions actually have data for a given project/snapshot.
WEIGHT_COST_ML = 0.30
WEIGHT_SCHEDULE_HEALTH = 0.20
WEIGHT_DIVERGENCE_HEALTH = 0.20
WEIGHT_ANOMALY = 0.20
# Deliberately the smallest weight - unverified/external sources must never
# dominate the score (SRS FR-020: external evidence is never represented as
# an official project fact).
WEIGHT_EXTERNAL_EVIDENCE = 0.10

ANOMALY_SEVERITY_SCORE = {"MODERATE": 40.0, "HIGH": 70.0, "CRITICAL": 100.0}
TIER_SCORE = {"WATCH": 25.0, "ELEVATED": 50.0, "HIGH": 75.0, "CRITICAL": 100.0}


@dataclass(frozen=True)
class RiskFusionResult:
    overall_risk: str  # LOW | MODERATE | ELEVATED | HIGH | CRITICAL | DATA_NOT_AVAILABLE
    risk_score: float | None  # 0-100
    confidence: float  # 0.0-1.0
    fusion_version: str


def _tier_for(value: float, thresholds: list[tuple[float, str]]) -> str | None:
    for threshold, label in thresholds:
        if value >= threshold:
            return label
    return None


def _cost_ml_score(prediction) -> float | None:
    if prediction is None:
        return None
    return prediction.probability * 100


def _schedule_health_score(health: HealthVector) -> float | None:
    if health.progress_gap is None:
        return None
    if health.progress_gap >= 0:
        return 0.0
    tier = _tier_for(-health.progress_gap, SCHEDULE_SHORTFALL_THRESHOLDS)
    return TIER_SCORE.get(tier, 0.0)


def _divergence_health_score(health: HealthVector) -> float | None:
    if health.expenditure_progress_divergence is None:
        return None
    tier = _tier_for(health.expenditure_progress_divergence, DIVERGENCE_THRESHOLDS)
    return TIER_SCORE.get(tier, 0.0)


def _anomaly_score(anomalies: list[Anomaly] | None) -> float | None:
    """`None` means anomaly detection could not run at all (too little
    history - see `anomaly.formulas.MIN_BASELINE_POINTS`), distinct from an
    empty list, which means it ran and found nothing (a real, available
    result contributing a clean 0.0 - not "unavailable")."""
    if anomalies is None:
        return None
    if not anomalies:
        return 0.0
    return max(ANOMALY_SEVERITY_SCORE.get(a.severity, 0.0) for a in anomalies)


def _external_evidence_score(evidence: list[FusedEvidence]) -> float | None:
    official = [e for e in evidence if e.category == OFFICIAL_EXTERNAL_SOURCE]
    secondary = [e for e in evidence if e.category == SECONDARY_SOURCE]
    if not official and not secondary:
        return None
    if official:
        return 100.0 * max(e.confidence for e in official)
    return 60.0 * max(e.confidence for e in secondary)


def fuse_risk(
    health: HealthVector,
    prediction,
    anomalies: list[Anomaly] | None,
    evidence: list[FusedEvidence],
) -> RiskFusionResult:
    dimensions = [
        (WEIGHT_COST_ML, _cost_ml_score(prediction)),
        (WEIGHT_SCHEDULE_HEALTH, _schedule_health_score(health)),
        (WEIGHT_DIVERGENCE_HEALTH, _divergence_health_score(health)),
        (WEIGHT_ANOMALY, _anomaly_score(anomalies)),
        (WEIGHT_EXTERNAL_EVIDENCE, _external_evidence_score(evidence)),
    ]
    available = [(w, s) for w, s in dimensions if s is not None]

    if not available:
        return RiskFusionResult(
            overall_risk="DATA_NOT_AVAILABLE", risk_score=None, confidence=0.0, fusion_version=RISK_FUSION_VERSION
        )

    total_weight = sum(w for w, _ in available)
    risk_score = sum(w * s for w, s in available) / total_weight
    overall_risk = risk_level_for_probability(min(max(risk_score / 100, 0.0), 1.0))

    confidence = len(available) / len(dimensions)
    external_only = [e for e in evidence if e.category in {OFFICIAL_EXTERNAL_SOURCE, SECONDARY_SOURCE}]
    if external_only and not any(e.category == OFFICIAL_EXTERNAL_SOURCE for e in external_only):
        confidence *= 0.85  # secondary-source-only external evidence is less reliable (FR-020)

    return RiskFusionResult(
        overall_risk=overall_risk,
        risk_score=round(risk_score, 2),
        confidence=round(confidence, 4),
        fusion_version=RISK_FUSION_VERSION,
    )
