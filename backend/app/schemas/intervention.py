from datetime import date

from pydantic import BaseModel


class RecommendationResponse(BaseModel):
    priority: str
    action_type: str
    action: str
    reason: str
    evidence_ids: list[str]
    review_area: str
    driver: str
    monitoring_level: str


class InterventionResponse(BaseModel):
    project_id: str
    project_name: str
    as_of_date: date
    overall_risk: str
    suggested_monitoring_level: str
    recommendations: list[RecommendationResponse]
