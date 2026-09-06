from pydantic import BaseModel


class CitationResponse(BaseModel):
    document_name: str
    page: int
    excerpt: str
    score: float


class ReviewEvidenceResponse(BaseModel):
    project_id: str
    project_name: str
    question: str
    answer: str
    citations: list[CitationResponse]
    summary_source: str
    summary_model: str | None
    evidence_found: bool
    searched_at: str
