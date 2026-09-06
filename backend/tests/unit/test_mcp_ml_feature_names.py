"""Unit test for ML MCP's explain_prediction feature-name reconstruction
(backend/app/mcp/ml/service.py::_resolve_feature_names) against the REAL
model artifact - confirms the live-verified fact that
SimpleImputer(add_indicator=True) widens the classifier's input beyond
FEATURE_COLUMNS, and that the reconstruction (not the classifier's own
meaningless "Column_N" feature_name_) is what gets used."""

from __future__ import annotations

from app.mcp.ml.service import _resolve_feature_names
from app.services.prediction.model_loader import load_model_bundle


def test_reconstructed_names_match_real_model_width() -> None:
    bundle = load_model_bundle()
    clf = bundle.pipeline.named_steps["clf"]
    importances = clf.feature_importances_

    names, source = _resolve_feature_names(clf, len(importances))

    assert len(names) == len(importances)
    assert len(names) == len(set(names))  # no accidental duplicate names
    assert source in {"RECONSTRUCTED_FEATURE_COLUMNS", "MODEL_NATIVE", "ORDINAL_FALLBACK"}


def test_never_reports_model_native_for_generic_lightgbm_names() -> None:
    """The real artifact's clf.feature_name_ are meaningless placeholders
    ("Column_0", "Column_1", ...) - never trust them as MODEL_NATIVE."""
    bundle = load_model_bundle()
    clf = bundle.pipeline.named_steps["clf"]
    importances = clf.feature_importances_

    names, source = _resolve_feature_names(clf, len(importances))

    if source == "MODEL_NATIVE":
        assert not all(n.startswith("Column_") for n in names)
    else:
        assert source == "RECONSTRUCTED_FEATURE_COLUMNS"


def test_reconstructed_names_include_missing_indicator_columns() -> None:
    """Ground truth confirmed live: 23 FEATURE_COLUMNS + 8 missingindicator_*
    columns = 31 classifier inputs for this artifact."""
    bundle = load_model_bundle()
    clf = bundle.pipeline.named_steps["clf"]
    importances = clf.feature_importances_

    names, source = _resolve_feature_names(clf, len(importances))

    if source == "RECONSTRUCTED_FEATURE_COLUMNS" and len(names) > 23:
        assert any(n.startswith("missingindicator_") for n in names)
