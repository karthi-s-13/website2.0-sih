from datetime import date

from pydantic import BaseModel


class WebEvidenceItemResponse(BaseModel):
    evidence_id: str
    topic: str
    source: str
    url: str
    title: str | None
    publication_date: date | None
    date_confidence: str
    finding: str
    project_relevance: float
    source_quality: str


class WebIntelligenceResponse(BaseModel):
    project_id: str
    project_name: str
    triggered: bool
    trigger_reason: str
    topics_searched: list[str]
    evidence: list[WebEvidenceItemResponse]
    warnings: list[str]
    searched_at: str
