from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Status = Literal["OK", "NOT_FOUND", "NOT_AVAILABLE", "ERROR"]


class CostRiskResponse(BaseModel):
    status: Status
    project_id: str
    prediction_date: str
    risk_type: str | None = None
    probability: float | None = None
    risk_level: str | None = None
    model_version: str | None = None
    feature_version: str | None = None
    leakage_check: str | None = None
    message: str | None = None


class TimeRiskResponse(BaseModel):
    status: Literal["NOT_FOUND", "NOT_AVAILABLE"]
    project_id: str
    prediction_date: str
    reason: str


class ModelMetadataResponse(BaseModel):
    status: Literal["OK", "NOT_AVAILABLE"]
    model_version: str | None = None
    model_type: str | None = None
    trained_at: str | None = None
    n_training_rows: int | None = None
    random_state: int | None = None
    optimal_threshold: float | None = None
    oof_metrics: dict[str, float] | None = None
    feature_engineering_version: str | None = None
    raw_feature_cols: list[str] | None = None
    message: str | None = None


class FeatureField(BaseModel):
    name: str
    unit: str


class FeatureSchemaResponse(BaseModel):
    status: Literal["OK", "NOT_AVAILABLE"]
    model_raw_input_columns: list[str] | None = None
    model_engineered_columns: list[str] | None = None
    model_feature_engineering_version: str | None = None
    phase2_feature_store_version: str | None = None
    phase2_feature_store_fields: list[FeatureField] | None = None
    message: str | None = None


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class ExplanationResponse(BaseModel):
    status: Status
    project_id: str
    prediction_date: str
    probability: float | None = None
    risk_level: str | None = None
    explanation_type: Literal["GLOBAL_FEATURE_IMPORTANCE", "NOT_AVAILABLE"] | None = None
    feature_names_source: Literal["RECONSTRUCTED_FEATURE_COLUMNS", "MODEL_NATIVE", "ORDINAL_FALLBACK"] | None = None
    feature_importances: list[FeatureImportance] | None = None
    model_version: str | None = None
    caveat: str | None = None
    message: str | None = None
