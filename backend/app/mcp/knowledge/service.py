"""Knowledge MCP (Phase 12): vector/hybrid search over the review-report
corpus (shares Document MCP's retrieval helper - no duplication) plus the
web-evidence store (Phase 8's `web_evidence` table - the only persisted
evidence store in this codebase; see EvidenceInput's docstring for the
explicit scope limitation against Phase 9's in-memory FusedEvidence).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.mcp._shared import resolve_query_embedding, run_hybrid_or_keyword_search, session_scope
from app.mcp.knowledge.schemas import (
    EvidenceInput,
    EvidenceItem,
    HybridResultItem,
    HybridSearchResponse,
    RetrieveEvidenceResponse,
    StoreEvidenceResponse,
    VectorResultItem,
    VectorSearchResponse,
)
from app.models.web_evidence import WebEvidence
from app.repositories.web_evidence_repository import get_evidence_for_project
from app.repositories.web_evidence_repository import store_evidence as _store_evidence_rows
from app.services.rag.vector_store import vector_search as _vector_search
from app.services.web.service import evidence_id

mcp = FastMCP(
    "knowledge",
    instructions="Vector/hybrid search over the review-report corpus, plus the web-evidence "
    "store (Phase 8's web_evidence table only - see store_evidence's scope note).",
)

SNIPPET_LENGTH = 500


def _snippet(text: str) -> str:
    return text if len(text) <= SNIPPET_LENGTH else text[:SNIPPET_LENGTH] + "..."


@mcp.tool()
def vector_search(query: str, top_k: int = 5, project_id: str | None = None) -> VectorSearchResponse:
    """Pure cosine-similarity vector search (no keyword/RRF blending - see
    hybrid_search for that). Requires a working embedding call; returns
    status="NOT_AVAILABLE" if none is available (no GEMINI_API_KEY / a
    failed call), since a pure-vector search cannot run without one."""
    settings = get_settings()
    with session_scope() as session:
        embedding = resolve_query_embedding(query, settings.gemini_api_key)
        if embedding is None:
            return VectorSearchResponse(status="NOT_AVAILABLE", query=query, embedding_used=False)

        results = _vector_search(session, embedding, top_k, project_id=project_id)
        items = [
            VectorResultItem(
                chunk_id=chunk.id, document_id=chunk.document_id, document_name=chunk.document.document_name,
                page=chunk.page, text_snippet=_snippet(chunk.text), distance=distance,
            )
            for chunk, distance in results
        ]
        return VectorSearchResponse(status="OK", query=query, embedding_used=True, results=items)


@mcp.tool()
def hybrid_search(
    query: str, top_k: int = 5, project_id: str | None = None, boost_terms: list[str] | None = None
) -> HybridSearchResponse:
    """Vector + keyword hybrid search (Reciprocal Rank Fusion), the same
    shared retrieval path Document MCP's search_documents uses - falls back
    to keyword-only when no embedding is available rather than returning
    nothing."""
    settings = get_settings()
    with session_scope() as session:
        ranked, embedding_used = run_hybrid_or_keyword_search(
            session, query, top_k, api_key=settings.gemini_api_key, project_id=project_id, boost_terms=boost_terms
        )
        items = [
            HybridResultItem(
                chunk_id=r.chunk.id, document_id=r.chunk.document_id, document_name=r.chunk.document.document_name,
                page=r.chunk.page, text_snippet=_snippet(r.chunk.text), score=r.score,
                matched_vector=r.matched_vector, matched_keyword=r.matched_keyword,
            )
            for r in ranked
        ]
        return HybridSearchResponse(status="OK", query=query, embedding_used=embedding_used, results=items)


@mcp.tool()
def store_evidence(project_id: str, items: list[EvidenceInput]) -> StoreEvidenceResponse:
    """Stores web-sourced evidence findings for a project (Phase 8's
    `web_evidence` table). Re-storing the same project_id/topic/url triple
    updates the existing row rather than duplicating it (content-addressed
    evidence_id, the same scheme Phase 8's own pipeline uses). Scope
    limitation: does NOT persist Phase 9's in-memory diagnosis-time
    FusedEvidence - see EvidenceInput's docstring."""
    with session_scope() as session:
        rows = [
            WebEvidence(
                evidence_id=evidence_id(project_id, item.url, item.topic),
                project_id=project_id,
                source_type="WEB",
                topic=item.topic,
                query_used=item.query_used,
                source=item.source,
                url=item.url,
                title=item.title,
                published_date=item.published_date,
                date_confidence=item.date_confidence,
                finding=item.finding,
                project_relevance=item.project_relevance,
                trust_tier=item.trust_tier,
                source_quality=item.source_quality,
            )
            for item in items
        ]
        _store_evidence_rows(session, rows)
        return StoreEvidenceResponse(status="OK", project_id=project_id, stored_count=len(rows))


@mcp.tool()
def retrieve_evidence(project_id: str) -> RetrieveEvidenceResponse:
    """All stored web-sourced evidence for a project (Phase 8's
    `web_evidence` table only - see store_evidence's scope note)."""
    with session_scope() as session:
        rows = get_evidence_for_project(session, project_id)
        items = [
            EvidenceItem(
                evidence_id=r.evidence_id, source_type=r.source_type, topic=r.topic, query_used=r.query_used,
                source=r.source, url=r.url, title=r.title, published_date=r.published_date,
                date_confidence=r.date_confidence, finding=r.finding, project_relevance=r.project_relevance,
                trust_tier=r.trust_tier, source_quality=r.source_quality,
                retrieved_at=r.retrieved_at.isoformat() if r.retrieved_at else "",
            )
            for r in rows
        ]
        return RetrieveEvidenceResponse(status="OK", project_id=project_id, evidence=items)
