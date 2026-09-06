"""Loads the pretrained cost-overrun model artifact (Phase 3: integrate the
existing .pkl, do not retrain it).

See docs/model_integration_notes.md for the full reverse-engineering
evidence behind ml/pipeline/feature_engineering.py, which this module
depends on to even unpickle the artifact (the pickle references the exact
dotted path `pipeline.feature_engineering.FeatureEngineer`).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")  # avoids a noisy, harmless
# subprocess-probe warning from joblib/loky in sandboxed environments.

REPO_ROOT = Path(__file__).resolve().parents[4]
ML_DIR = REPO_ROOT / "ml"
MODEL_PATH = REPO_ROOT / "model" / "lightgbm_cost_overrun_model.pkl"

# Version tag for OUR reconstruction of the model's preprocessing logic
# (ml/pipeline/feature_engineering.py) - distinct from, and unrelated to,
# Phase 2's "features-v1" feature store. Bump this if that reconstruction
# changes (e.g. a corrected keyword list).
FEATURE_ENGINEERING_VERSION = "ml-fe-v1-reconstructed"

RISK_TYPE = "cost_overrun"


@dataclass(frozen=True)
class ModelBundle:
    pipeline: Any
    model_type: str
    raw_feature_cols: list[str]
    optimal_threshold: float
    oof_metrics: dict[str, float]
    trained_at: str
    n_training_rows: int
    random_state: int
    model_version: str


def _ensure_ml_on_path() -> None:
    ml_dir_str = str(ML_DIR)
    if ml_dir_str not in sys.path:
        sys.path.insert(0, ml_dir_str)


@lru_cache
def load_model_bundle() -> ModelBundle:
    from app.core.errors import ModelUnavailableError

    _ensure_ml_on_path()

    if not MODEL_PATH.exists():
        raise ModelUnavailableError(f"model artifact not found at {MODEL_PATH}")

    try:
        import joblib

        artifact = joblib.load(MODEL_PATH)
    except Exception as exc:  # noqa: BLE001 - any load failure means "unavailable"
        raise ModelUnavailableError(f"failed to load model artifact: {exc}") from exc

    pipeline = artifact["pipeline"]
    _validate_feature_contract(pipeline)

    trained_at = artifact["trained_at"]
    model_version = f"cost-overrun-lightgbm-{trained_at}"

    return ModelBundle(
        pipeline=pipeline,
        model_type=artifact["model_type"],
        raw_feature_cols=list(artifact["raw_feature_cols"]),
        optimal_threshold=float(artifact["optimal_threshold"]),
        oof_metrics=dict(artifact["oof_metrics"]),
        trained_at=trained_at,
        n_training_rows=int(artifact["n_training_rows"]),
        random_state=int(artifact["random_state"]),
        model_version=model_version,
    )


def _validate_feature_contract(pipeline: Any) -> None:
    """Belt-and-braces check (Phase 3: "validate feature ordering"): the
    reconstructed FeatureEngineer's output must match what the fitted
    imputer was actually trained on, name-for-name, in order."""
    from pipeline.feature_engineering import FEATURE_COLUMNS

    imputer = pipeline.named_steps["impute"]
    expected = list(imputer.feature_names_in_)
    if FEATURE_COLUMNS != expected:
        from app.core.errors import ModelUnavailableError

        raise ModelUnavailableError(
            "feature engineering contract mismatch: "
            f"reconstruction produces {FEATURE_COLUMNS}, model expects {expected}"
        )
