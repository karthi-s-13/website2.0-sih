from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel

Status = Literal["OK", "NOT_FOUND", "NOT_AVAILABLE"]


class MetricResponse(BaseModel):
    status: Status
    project_id: str
    snapshot_month: date | None = None
    value: Any = None
    formula_version: str | None = None
    inputs: dict = {}
    calculated_at: str | None = None
    message: str | None = None


class RecentTrendModel(BaseModel):
    monthly_progress_change: float | None
    monthly_expenditure_change: float | None
    progress_slope: float | None
    expenditure_slope: float | None
    consecutive_stagnant_months: int
    label: str


class MilestoneHealthModel(BaseModel):
    status: str
    total: int
    completed: int
    delayed: int


class HealthResponse(BaseModel):
    status: Status
    project_id: str
    snapshot_month: date | None = None
    overall_health: str | None = None
    cost_utilisation: float | None = None
    schedule_utilisation: float | None = None
    physical_progress: float | None = None
    expected_progress: float | None = None
    progress_gap: float | None = None
    expenditure_progress_divergence: float | None = None
    recent_trend: RecentTrendModel | None = None
    milestone_health: MilestoneHealthModel | None = None
    input_observation_count: int | None = None
    formula_version: str | None = None
    message: str | None = None


class AnomalyItem(BaseModel):
    anomaly_type: str
    severity: str
    score: float
    description: str
    month: date


class AnomalyResponse(BaseModel):
    status: Status
    project_id: str
    snapshot_month: date | None = None
    anomalies: list[AnomalyItem] = []
    unavailable_types: list[str] = []
    input_observation_count: int | None = None
    message: str | None = None
