from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

Status = Literal["OK", "NOT_FOUND"]


class ProjectResponse(BaseModel):
    status: Status
    project_id: str
    project_name: str | None = None
    agency: str | None = None
    agency_code: str | None = None
    ministry: str | None = None
    sector: str | None = None
    state: str | None = None
    original_cost_crore: float | None = None
    revised_cost_crore: float | None = None
    date_of_approval: date | None = None
    start_date: date | None = None
    original_completion_date: date | None = None
    revised_completion_date: date | None = None
    current_status: str | None = None
    first_observation_month: date | None = None
    latest_observation_month: date | None = None
    observation_count: int | None = None


class ObservationItem(BaseModel):
    observation_month: date
    report_label: str
    record_type: str | None
    date_of_approval: date | None
    start_date: date | None
    target_completion_date: date | None
    revised_completion_date: date | None
    original_cost_crore: float | None
    revised_cost_crore: float | None
    cumulative_expenditure_crore: float | None
    physical_progress_percent: float | None
    notes: str | None
    source_file: str
    source_row: int


class ObservationsResponse(BaseModel):
    status: Status
    project_id: str
    count: int
    observations: list[ObservationItem]


class MilestoneItem(BaseModel):
    milestone_name: str
    planned_date: date | None
    actual_date: date | None
    status: str | None


class MilestonesResponse(BaseModel):
    status: Status
    project_id: str
    count: int
    unavailable: bool
    milestones: list[MilestoneItem]


class EventItem(BaseModel):
    event_month: date
    event_type: str
    description: str
    previous_value: str | None
    new_value: str | None


class EventsResponse(BaseModel):
    status: Status
    project_id: str
    count: int
    events: list[EventItem]
