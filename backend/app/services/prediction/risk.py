"""Probability -> risk-level classification (SRS FR-025).

    0-29    LOW
    30-49   MODERATE
    50-69   ELEVATED
    70-84   HIGH
    85-100  CRITICAL

Thresholds are expressed on the probability*100 scale and kept as named
constants so they stay easy to find and adjust; FR-025 notes actual
thresholds should be validated against historical evaluation data (Phase 14).
"""

from __future__ import annotations

MODERATE_THRESHOLD = 30
ELEVATED_THRESHOLD = 50
HIGH_THRESHOLD = 70
CRITICAL_THRESHOLD = 85


def risk_level_for_probability(probability: float) -> str:
    if not 0.0 <= probability <= 1.0:
        raise ValueError(f"probability must be within [0, 1], got {probability}")

    score = probability * 100
    if score >= CRITICAL_THRESHOLD:
        return "CRITICAL"
    if score >= HIGH_THRESHOLD:
        return "HIGH"
    if score >= ELEVATED_THRESHOLD:
        return "ELEVATED"
    if score >= MODERATE_THRESHOLD:
        return "MODERATE"
    return "LOW"
