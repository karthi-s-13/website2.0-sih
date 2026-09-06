from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

Status = Literal["OK", "NOT_AVAILABLE"]


class VectorResultItem(BaseModel):
    chunk_id: int
    document_id: str
    document_name: str
    page: int
    text_snippet: str
    distance: float


class VectorSearchResponse(BaseModel):
    status: Status
    query: str
    embedding_used: bool
    results: list[VectorResultItem] = []


class HybridResultItem(BaseModel):
    chunk_id: int
    document_id: str
    document_name: str
    page: int
    text_snippet: str
    score: float
    matched_vector: bool
    matched_keyword: bool


class HybridSearchResponse(BaseModel):
    status: Literal["OK"]
    query: str
    embedding_used: bool
    results: list[HybridResultItem] = []


class EvidenceInput(BaseModel):
    """Scope limitation: this wraps `web_evidence` only (the sole persisted
    evidence store in this codebase) - it does NOT persist Phase 9's
    in-memory diagnosis-time FusedEvidence (health/anomaly/ML/review-derived
    evidence), which is recomputed live and never stored under this or any
    other tool."""

    topic: str
    query_used: str
    source: str
    url: str
    title: str | None = None
    published_date: date | None = None
    date_confidence: str = "UNVERIFIED"
    finding: str
    project_relevance: float
    trust_tier: str
    source_quality: str


class StoreEvidenceResponse(BaseModel):
    status: Literal["OK"]
    project_id: str
    stored_count: int


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: str
    topic: str
    query_used: str
    source: str
    url: str
    title: str | None
    published_date: date | None
    date_confidence: str
    finding: str
    project_relevance: float
    trust_tier: str
    source_quality: str
    retrieved_at: str


class RetrieveEvidenceResponse(BaseModel):
    status: Literal["OK"]
    project_id: str
    evidence: list[EvidenceItem] = []
