from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

Status = Literal["OK", "NOT_FOUND", "NOT_AVAILABLE"]


class SearchResultItem(BaseModel):
    chunk_id: int
    document_id: str
    document_name: str
    page: int
    text_snippet: str
    score: float
    matched_vector: bool
    matched_keyword: bool
    sector: str | None
    project_id: str | None


class SearchDocumentsResponse(BaseModel):
    status: Status
    query: str
    embedding_used: bool
    results: list[SearchResultItem] = []


class ChunkItem(BaseModel):
    chunk_index: int
    page: int
    text: str
    char_count: int
    extraction_method: str
    sector: str | None
    project_id: str | None


class ChunksResponse(BaseModel):
    status: Status
    document_id: str
    chunks: list[ChunkItem] = []


class DocumentPageChunk(BaseModel):
    chunk_index: int
    text: str
    extraction_method: str


class DocumentPageResponse(BaseModel):
    status: Status
    document_id: str
    document_name: str | None = None
    page: int
    chunks: list[DocumentPageChunk] = []
    full_text: str = ""


class DocumentMetadataResponse(BaseModel):
    status: Status
    document_id: str
    document_name: str | None = None
    source_file: str | None = None
    edition_date: date | None = None
    source_type: str | None = None
    page_count: int | None = None
    ingested_at: str | None = None
    chunk_count: int | None = None


class CitationItem(BaseModel):
    document_name: str
    page: int
    excerpt: str
    score: float


class ProjectMentionsResponse(BaseModel):
    status: Status
    project_id: str
    project_name: str | None = None
    question: str | None = None
    answer: str | None = None
    citations: list[CitationItem] = []
    evidence_found: bool | None = None
    summary_source: str | None = None
    summary_model: str | None = None
    searched_at: str | None = None
