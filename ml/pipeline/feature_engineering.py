"""Compatibility shim for `model/lightgbm_cost_overrun_model.pkl`.

The pickle was produced (via joblib) from an sklearn Pipeline whose first
step is an instance of `pipeline.feature_engineering.FeatureEngineer` - a
custom class. Unpickling a custom class only requires the class to be
*importable at this exact dotted path*; pickle restores the instance's FITTED
STATE (`__dict__`) directly, but the class's CODE (its methods) is not part
of the pickle at all and must come from wherever the class is defined when
loading.

That means:
  - `rare_threshold`, `schedule_ratio_clip`, `agency_keep_`, `agency_freq_map_`,
    `state_keep_`, `state_freq_map_` below are NOT hardcoded - they are
    whatever values the pickle restores onto the instance (the real, fitted
    values from training).
  - `transform()` (the actual LOGIC) is NOT recoverable from the pickle. The
    implementation below is a reconstruction, not the original source. It is
    evidence-based, not guessed outright - see docs/model_integration_notes.md
    for the full derivation and every assumption made explicit. Do not treat
    this as ground truth equal to the original training code; treat it as the
    best faithful reconstruction achievable without that code, subject to
    revision if evidence emerges that contradicts it.
"""

from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# Exact order, from the fitted SimpleImputer's `feature_names_in_` (ground
# truth recovered directly from the pickle - not guessed).
FEATURE_COLUMNS: list[str] = [
    "planned_duration_months",
    "snapshot_elapsed_months",
    "schedule_progress_ratio",
    "original_cost",
    "cumulative_expenditure",
    "cost_burn_ratio",
    "physical_progress",
    "progress_spend_discrepancy",
    "progress_time_discrepancy",
    "edition_year",
    "edition_month",
    "project_name_length",
    "project_name_word_count",
    "kw_road",
    "kw_bridge",
    "kw_power_solar",
    "kw_pipeline_oil_gas",
    "kw_rail_metro",
    "kw_port",
    "kw_irrigation",
    "kw_building",
    "agency_freq",
    "state_freq",
]

# Raw input columns, from the pickle's stored `raw_feature_cols` metadata
# (ground truth). "doa" = date of approval; "original_target_doa" = original
# target completion date. No "revised_cost" column exists here - the model
# was not trained on it, so integration cannot leak it either.
RAW_FEATURE_COLUMNS: list[str] = [
    "edition",
    "project_name",
    "agency",
    "state",
    "doa",
    "original_target_doa",
    "original_cost",
    "cumulative_expenditure",
    "physical_progress",
]

# Best-effort keyword reconstruction for the kw_* columns (their names are
# the only evidence available - no keyword lists survive in the pickle).
# Kept intentionally simple; these are weak signal features feeding a
# gradient-boosted ensemble alongside 15 stronger features, so imperfect
# recall here has bounded impact on the overall prediction.
_KEYWORDS: dict[str, tuple[str, ...]] = {
    "kw_road": ("road", "highway", "expressway"),
    "kw_bridge": ("bridge", "flyover", "viaduct"),
    "kw_power_solar": (
        "power",
        "solar",
        "transmission",
        "transformer",
        "substation",
        "grid",
        "hydro",
        "thermal",
        "energy",
    ),
    "kw_pipeline_oil_gas": ("pipeline", "oil", "gas", "refinery", "petroleum", "lng", "crude"),
    "kw_rail_metro": ("rail", "railway", "metro", "track", "gauge"),
    "kw_port": ("port", "harbour", "harbor", "jetty", "dock"),
    "kw_irrigation": ("irrigation", "canal", "dam", "reservoir", "barrage"),
    "kw_building": ("building", "airport", "hospital", "campus", "terminal", "construction"),
}

_MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _to_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, float) and np.isnan(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return pd.to_datetime(text).date()


def _parse_edition(value: object) -> date | None:
    """Parses an "edition" value. Accepts either a real date (already
    normalized to the 1st of the month upstream) or a "Month YYYY" string,
    matching the two representations seen in the real Flash Report data."""
    parsed = _to_date(value) if isinstance(value, date | datetime | pd.Timestamp) else None
    if parsed is not None:
        return parsed
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    month_str, _, year_str = text.rpartition(" ")
    month_num = _MONTH_NAMES.get(month_str.strip().lower())
    if month_num is None or not year_str.isdigit():
        return None
    return date(int(year_str), month_num, 1)


def _months_between(earlier: date, later: date) -> int:
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Reconstructed shim - see module docstring. `__init__` defaults mirror
    the fitted values only for the case where this class is instantiated
    fresh (e.g. in tests); when unpickled, the real fitted values overwrite
    these via `__dict__` restoration, not `__init__`.
    """

    def __init__(
        self,
        rare_threshold: float = 0.01,
        schedule_ratio_clip: tuple[float, float] = (-1.0, 3.0),
    ) -> None:
        self.rare_threshold = rare_threshold
        self.schedule_ratio_clip = schedule_ratio_clip

    def fit(self, X, y=None):  # noqa: N803
        raise NotImplementedError(
            "This FeatureEngineer is an inference-only reconstruction of a "
            "pretrained model's preprocessing step; fitting/retraining is "
            "intentionally not supported here (Phase 3: integrate, don't retrain)."
        )

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:  # noqa: N803
        missing = [c for c in RAW_FEATURE_COLUMNS if c not in X.columns]
        if missing:
            raise ValueError(f"missing required raw feature columns: {missing}")

        doa = X["doa"].map(_to_date)
        target = X["original_target_doa"].map(_to_date)
        edition = X["edition"].map(_parse_edition)

        planned_duration = pd.Series(
            [
                _months_between(d, t) if d is not None and t is not None else np.nan
                for d, t in zip(doa, target, strict=True)
            ],
            index=X.index,
            dtype=float,
        )
        elapsed = pd.Series(
            [
                _months_between(d, e) if d is not None and e is not None else np.nan
                for d, e in zip(doa, edition, strict=True)
            ],
            index=X.index,
            dtype=float,
        )

        lo, hi = self.schedule_ratio_clip
        with np.errstate(divide="ignore", invalid="ignore"):
            raw_ratio = elapsed / planned_duration.replace(0, np.nan)
        schedule_ratio = raw_ratio.clip(lower=lo, upper=hi)

        original_cost = pd.to_numeric(X["original_cost"], errors="coerce")
        cum_exp = pd.to_numeric(X["cumulative_expenditure"], errors="coerce")
        progress = pd.to_numeric(X["physical_progress"], errors="coerce")

        cost_burn = cum_exp / original_cost.where(original_cost > 0)
        progress_ratio = progress / 100.0

        out = pd.DataFrame(index=X.index)
        out["planned_duration_months"] = planned_duration
        out["snapshot_elapsed_months"] = elapsed
        out["schedule_progress_ratio"] = schedule_ratio
        out["original_cost"] = original_cost
        out["cumulative_expenditure"] = cum_exp
        out["cost_burn_ratio"] = cost_burn
        out["physical_progress"] = progress
        out["progress_spend_discrepancy"] = cost_burn - progress_ratio
        out["progress_time_discrepancy"] = progress_ratio - schedule_ratio
        out["edition_year"] = [e.year if e is not None else np.nan for e in edition]
        out["edition_month"] = [e.month if e is not None else np.nan for e in edition]

        names = X["project_name"].fillna("").astype(str)
        out["project_name_length"] = names.str.len().astype(float)
        out["project_name_word_count"] = names.str.split().apply(len).astype(float)

        lowered = names.str.lower()
        for col, keywords in _KEYWORDS.items():
            out[col] = lowered.apply(lambda text, kws=keywords: float(any(k in text for k in kws)))

        out["agency_freq"] = X["agency"].map(self._encode_agency)
        out["state_freq"] = X["state"].map(self._encode_state)

        return out[FEATURE_COLUMNS]

    def _encode_agency(self, value: object) -> float:
        key = "MISSING" if value is None or (isinstance(value, float) and np.isnan(value)) else str(value).strip().upper()
        if key not in self.agency_keep_:
            key = "OTHER"
        return self.agency_freq_map_.get(key, self.agency_freq_map_["OTHER"])

    def _encode_state(self, value: object) -> float:
        key = "MISSING" if value is None or (isinstance(value, float) and np.isnan(value)) else str(value).strip().upper()
        if key not in self.state_keep_:
            key = "OTHER"
        return self.state_freq_map_.get(key, self.state_freq_map_["OTHER"])

    def get_feature_names_out(self, input_features=None):
        return np.array(FEATURE_COLUMNS)
