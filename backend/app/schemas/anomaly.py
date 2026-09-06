from datetime import date

from pydantic import BaseModel


class AnomalyResponse(BaseModel):
    anomaly_type: str
    severity: str
    score: float
    description: str
    month: date


class AnomalyResultResponse(BaseModel):
    project_id: str
    snapshot_month: date
    anomalies: list[AnomalyResponse]
    unavailable_types: list[str]
    input_observation_count: int
