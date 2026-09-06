from datetime import date

from pydantic import BaseModel


class TimelineEntryResponse(BaseModel):
    month: date
    title: str
    description: str
    source_type: str
    evidence_ref: str


class MajorChangeResponse(BaseModel):
    month: date
    change_type: str
    description: str
    source_type: str
    previous_value: str | None
    new_value: str | None


class RiskSignalResponse(BaseModel):
    month: date
    signal_type: str
    description: str
    source_type: str
    severity: str | None


class HistoryRequest(BaseModel):
    question: str = "What happened to this project?"
    as_of_date: date | None = None


class HistoryResponse(BaseModel):
    project_id: str
    project_name: str
    as_of_date: date
    question: str
    timeline: list[TimelineEntryResponse]
    major_changes: list[MajorChangeResponse]
    current_state: str
    historical_risk_signals: list[RiskSignalResponse]
    summary_source: str
    summary_model: str | None
