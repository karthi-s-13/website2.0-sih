from datetime import date

from pydantic import BaseModel


class RecentTrendResponse(BaseModel):
    monthly_progress_change: float | None
    monthly_expenditure_change: float | None
    progress_slope: float | None
    expenditure_slope: float | None
    consecutive_stagnant_months: int
    label: str


class MilestoneHealthResponse(BaseModel):
    status: str
    total: int
    completed: int
    delayed: int


class HealthResponse(BaseModel):
    project_id: str
    snapshot_month: date
    overall_health: str
    cost_utilisation: float | None
    schedule_utilisation: float | None
    physical_progress: float | None
    expected_progress: float | None
    progress_gap: float | None
    expenditure_progress_divergence: float | None
    recent_trend: RecentTrendResponse
    milestone_health: MilestoneHealthResponse
