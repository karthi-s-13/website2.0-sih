"""ML MCP (Phase 12): the pretrained cost-overrun model (Phase 3) and its
metadata. `predict_time_risk` and `explain_prediction` are honest about two
real gaps in this codebase - see their docstrings.
"""

from __future__ import annotations

import dataclasses
from datetime import date

from mcp.server.fastmcp import FastMCP

from app.core.errors import AppError
from app.mcp._shared import error_envelope, session_scope
from app.mcp.ml.schemas import (
    CostRiskResponse,
    ExplanationResponse,
    FeatureField,
    FeatureImportance,
    FeatureSchemaResponse,
    ModelMetadataResponse,
    TimeRiskResponse,
)
from app.repositories.project_repository import get_project
from app.services.features.formulas import FeatureVector
from app.services.features.pipeline import FEATURE_VERSION
from app.services.prediction.model_loader import FEATURE_ENGINEERING_VERSION, load_model_bundle
from app.services.prediction.service import predict_cost_overrun

mcp = FastMCP(
    "ml",
    instructions="The pretrained ML cost-overrun model (Phase 3): prediction, metadata, "
    "feature schema, and global feature-importance explanation.",
)

# unit, per features/formulas.py's own module docstring - kept here (not
# re-derived from the docstring text) so a missing entry fails loudly via
# the assertion below rather than silently omitting a field.
_FEATURE_UNITS: dict[str, str] = {
    "cost_utilisation": "ratio",
    "expenditure_growth": "relative_rate",
    "monthly_expenditure_growth": "crore",
    "schedule_utilisation": "ratio",
    "physical_progress": "percentage_points",
    "expected_progress": "percentage_points",
    "progress_gap": "percentage_points",
    "expenditure_progress_divergence": "ratio",
    "monthly_progress_change": "percentage_points",
    "rolling_progress_change": "percentage_points",
    "rolling_expenditure_change": "crore",
    "project_age_months": "months",
    "remaining_schedule_months": "months",
    "remaining_cost_budget_crore": "crore",
}
_EXCLUDED_FEATURE_VECTOR_FIELDS = {"snapshot_month", "input_observation_count"}


def _phase2_feature_fields() -> list[FeatureField]:
    names = [f.name for f in dataclasses.fields(FeatureVector) if f.name not in _EXCLUDED_FEATURE_VECTOR_FIELDS]
    missing = [n for n in names if n not in _FEATURE_UNITS]
    assert not missing, f"_FEATURE_UNITS is missing units for FeatureVector fields: {missing}"
    return [FeatureField(name=n, unit=_FEATURE_UNITS[n]) for n in names]


@mcp.tool()
def predict_cost_risk(project_id: str, prediction_date: date) -> CostRiskResponse:
    """Cost-overrun risk probability for a project as of prediction_date,
    using only data at or before that date (point-in-time discipline
    enforced by the underlying Phase 3 service - a leakage violation blocks
    the prediction rather than returning a fabricated result)."""
    with session_scope() as session:
        try:
            result = predict_cost_overrun(session, project_id, prediction_date)
        except AppError as exc:
            return CostRiskResponse(
                **error_envelope(exc), project_id=project_id, prediction_date=prediction_date.isoformat()
            )
        return CostRiskResponse(
            status="OK",
            project_id=result.project_id,
            prediction_date=result.prediction_date,
            risk_type=result.risk_type,
            probability=result.probability,
            risk_level=result.risk_level,
            model_version=result.model_version,
            feature_version=result.feature_version,
            leakage_check=result.leakage_check,
        )


@mcp.tool()
def predict_time_risk(project_id: str, prediction_date: date) -> TimeRiskResponse:
    """Time (schedule) overrun risk. No time-overrun model has ever been
    built in this system (Phase 3 built cost-overrun only) - this always
    honestly returns NOT_AVAILABLE rather than fabricating a probability."""
    with session_scope() as session:
        project = get_project(session, project_id)
        if project is None:
            return TimeRiskResponse(
                status="NOT_FOUND",
                project_id=project_id,
                prediction_date=prediction_date.isoformat(),
                reason=f"project {project_id} not found",
            )
        return TimeRiskResponse(
            status="NOT_AVAILABLE",
            project_id=project_id,
            prediction_date=prediction_date.isoformat(),
            reason=(
                "No time-overrun prediction model is currently deployed. Phase 3 built a "
                "cost-overrun model only; see docs/development_phases.md Phase 3/11."
            ),
        )


@mcp.tool()
def get_model_metadata() -> ModelMetadataResponse:
    """Metadata for the loaded cost-overrun model artifact (version,
    training time, row count, threshold, out-of-fold metrics)."""
    try:
        bundle = load_model_bundle()
    except AppError as exc:
        return ModelMetadataResponse(status="NOT_AVAILABLE", message=exc.message)
    return ModelMetadataResponse(
        status="OK",
        model_version=bundle.model_version,
        model_type=bundle.model_type,
        trained_at=bundle.trained_at,
        n_training_rows=bundle.n_training_rows,
        random_state=bundle.random_state,
        optimal_threshold=bundle.optimal_threshold,
        oof_metrics=bundle.oof_metrics,
        feature_engineering_version=FEATURE_ENGINEERING_VERSION,
        raw_feature_cols=bundle.raw_feature_cols,
    )


@mcp.tool()
def get_feature_schema() -> FeatureSchemaResponse:
    """The model's own raw/engineered feature columns (Phase 3, model-fed),
    kept visibly distinct from Phase 2's independent point-in-time feature
    store (`project_monthly_features`) - the two are unrelated systems that
    happen to share underlying concepts (see model_loader.py's own
    docstring warning)."""
    from pipeline.feature_engineering import FEATURE_COLUMNS

    try:
        bundle = load_model_bundle()
    except AppError as exc:
        return FeatureSchemaResponse(status="NOT_AVAILABLE", message=exc.message)

    return FeatureSchemaResponse(
        status="OK",
        model_raw_input_columns=bundle.raw_feature_cols,
        model_engineered_columns=FEATURE_COLUMNS,
        model_feature_engineering_version=FEATURE_ENGINEERING_VERSION,
        phase2_feature_store_version=FEATURE_VERSION,
        phase2_feature_store_fields=_phase2_feature_fields(),
    )


def _resolve_feature_names(clf, n_importances: int) -> tuple[list[str], str]:  # noqa: ANN001
    """Reconstructs real names for the classifier's `n_importances` inputs.

    Ground truth, verified live against the actual model artifact: the
    fitted `SimpleImputer(add_indicator=True)` widens its 23 named columns
    (`FEATURE_COLUMNS`) with one `missingindicator_<col>` per column that
    had a missing value during training (`imputer.indicator_.features_`),
    giving 31 total inputs to `clf`. `clf.feature_name_` (LightGBM's own
    trained names) exist and match this length, but are meaningless
    (`"Column_0"`, `"Column_1"`, ...) - sklearn never passed real column
    names through to the classifier - so real names must be reconstructed
    from the imputer, not read off the classifier."""
    from pipeline.feature_engineering import FEATURE_COLUMNS

    try:
        bundle = load_model_bundle()
        imputer = bundle.pipeline.named_steps["impute"]
        indicator = getattr(imputer, "indicator_", None)
        if indicator is not None and getattr(imputer, "add_indicator", False):
            indicator_names = [f"missingindicator_{FEATURE_COLUMNS[i]}" for i in indicator.features_]
            reconstructed = FEATURE_COLUMNS + indicator_names
            if len(reconstructed) == n_importances:
                return reconstructed, "RECONSTRUCTED_FEATURE_COLUMNS"
    except Exception:  # noqa: BLE001 - reconstruction is best-effort, fall through
        pass

    if len(FEATURE_COLUMNS) == n_importances:
        return FEATURE_COLUMNS, "RECONSTRUCTED_FEATURE_COLUMNS"

    names = getattr(clf, "feature_name_", None)
    is_generic = names is not None and all(n.startswith("Column_") for n in names)
    if names is not None and len(names) == n_importances and not is_generic:
        return list(names), "MODEL_NATIVE"

    return [f"feature_{i}" for i in range(n_importances)], "ORDINAL_FALLBACK"


@mcp.tool()
def explain_prediction(project_id: str, prediction_date: date) -> ExplanationResponse:
    """Explains a cost-overrun prediction via the LightGBM classifier's own
    trained global feature importances - NOT a per-prediction (e.g. SHAP)
    attribution specific to this project's own input values, since no such
    method is implemented in this codebase. Grounds the explanation in a
    real prediction first (same NOT_FOUND/NOT_AVAILABLE/ERROR mapping as
    predict_cost_risk)."""
    with session_scope() as session:
        try:
            prediction = predict_cost_overrun(session, project_id, prediction_date)
        except AppError as exc:
            return ExplanationResponse(
                **error_envelope(exc), project_id=project_id, prediction_date=prediction_date.isoformat()
            )

    bundle = load_model_bundle()
    clf = bundle.pipeline.named_steps["clf"]
    importances = getattr(clf, "feature_importances_", None)

    if importances is None:
        return ExplanationResponse(
            status="OK",
            project_id=project_id,
            prediction_date=prediction.prediction_date,
            probability=prediction.probability,
            risk_level=prediction.risk_level,
            explanation_type="NOT_AVAILABLE",
            model_version=prediction.model_version,
            caveat=(
                "The loaded model does not expose feature importances; no SHAP or other "
                "per-prediction explanation method is implemented in this codebase."
            ),
        )

    names, source = _resolve_feature_names(clf, len(importances))
    pairs = sorted(zip(names, (float(v) for v in importances), strict=True), key=lambda p: p[1], reverse=True)

    return ExplanationResponse(
        status="OK",
        project_id=project_id,
        prediction_date=prediction.prediction_date,
        probability=prediction.probability,
        risk_level=prediction.risk_level,
        explanation_type="GLOBAL_FEATURE_IMPORTANCE",
        feature_names_source=source,
        feature_importances=[FeatureImportance(feature=n, importance=v) for n, v in pairs],
        model_version=prediction.model_version,
        caveat=(
            "This reflects the model's overall global feature importances learned during "
            "training, not a per-prediction (e.g. SHAP) attribution specific to this "
            "project's own input values."
        ),
    )
