from datetime import date

from pydantic import BaseModel


class PredictionRequest(BaseModel):
    prediction_date: date


class PredictionResponse(BaseModel):
    project_id: str
    prediction_date: str
    risk_type: str
    probability: float
    risk_level: str
    model_version: str
    feature_version: str
    leakage_check: str


class ProjectSummary(BaseModel):
    project_id: str
    project_name: str
    agency: str | None = None
    state: str | None = None
    sector: str | None = None
    original_cost_crore: float | None = None
    revised_cost_crore: float | None = None
    cumulative_expenditure_crore: float | None = None
    first_observation_month: date | None = None
    latest_observation_month: date | None = None
    observation_count: int


class ModelInfoResponse(BaseModel):
    model_type: str
    model_version: str
    feature_version: str
    raw_feature_cols: list[str]
    optimal_threshold: float
    oof_metrics: dict[str, float]
    trained_at: str
    n_training_rows: int
