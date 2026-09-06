from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

Status = Literal["OK", "NOT_AVAILABLE"]


class WebSearchResultItem(BaseModel):
    title: str
    url: str
    content: str
    published_date_raw: str | None = None


class SearchWebResponse(BaseModel):
    status: Status
    query: str
    results: list[WebSearchResultItem] = []
    warning: str | None = None


class FetchSourceResponse(BaseModel):
    status: Literal["OK", "REJECTED", "REDIRECT", "ERROR"]
    url: str
    final_url: str | None = None
    status_code: int | None = None
    content_type: str | None = None
    content_text: str | None = None
    truncated: bool = False
    redirect_location: str | None = None
    rejected_reason: Literal["UNSAFE_SCHEME", "UNSAFE_HOST", "DNS_RESOLUTION_FAILED"] | None = None
    message: str | None = None


class VerifySourceResponse(BaseModel):
    status: Literal["OK"]
    url: str
    domain: str | None = None
    trust_tier: str
    source_quality: str
    published_date: date | None = None
    date_confidence: Literal["VERIFIED", "UNVERIFIED"] | None = None


class ClaimItem(BaseModel):
    url: str
    title: str
    finding: str
    project_relevance: float
    trust_tier: str
    source_quality: str


class ExtractClaimResponse(BaseModel):
    status: Literal["OK"]
    topic: str
    source: Literal["LLM", "DETERMINISTIC_FALLBACK"]
    claims: list[ClaimItem] = []
