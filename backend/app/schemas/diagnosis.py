from datetime import date

from pydantic import BaseModel


class DriverResponse(BaseModel):
    rank: int
    driver: str
    severity: str
    evidence_ids: list[str]
    driver_key: str


class FusedEvidenceResponse(BaseModel):
    evidence_id: str
    category: str
    description: str
    confidence: float
    source_label: str
    topic: str | None
    severity: str | None
    month: date | None


class DiagnosisResponse(BaseModel):
    project_id: str
    project_name: str
    as_of_date: date
    overall_risk: str
    risk_score: float | None
    confidence: float
    fusion_version: str
    drivers: list[DriverResponse]
    evidence: list[FusedEvidenceResponse]
