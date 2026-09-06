"""Shared helpers for the Phase 12 MCP servers (backend/app/mcp/<name>/).

Every MCP server is a standalone process (mcp_servers/<name>/main.py), not a
FastAPI request handler - there is no `Depends(get_db)` request scope to
reuse, so `session_scope()` gives each tool call its own short-lived session,
the same lifecycle every `scripts/*.py` CLI in this repo already uses.

`run_hybrid_or_keyword_search` is the one retrieval helper shared by Document
MCP's `search_documents` and Knowledge MCP's `hybrid_search`, so the
embedding-unavailable-falls-back-to-keyword-search behaviour
`rag/service.py::search_review_evidence` already established is not
reimplemented twice.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.errors import AppError, DataLeakageError, DataQualityFailureError, ModelUnavailableError, NotFoundError
from app.services.rag.embeddings import EmbeddingUnavailableError, embed_query
from app.services.rag.retrieval import RankedChunk, hybrid_search
from app.services.rag.vector_store import keyword_search

ERROR_STATUS_MAP: dict[type[AppError], str] = {
    NotFoundError: "NOT_FOUND",
    DataQualityFailureError: "NOT_AVAILABLE",
    ModelUnavailableError: "NOT_AVAILABLE",
    DataLeakageError: "ERROR",
}


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def status_for_error(exc: AppError) -> str:
    """Never mask a DATA_LEAKAGE_DETECTED failure as merely unavailable -
    every other AppError degrades to an honest NOT_AVAILABLE/NOT_FOUND."""
    return ERROR_STATUS_MAP.get(type(exc), "ERROR")


def error_envelope(exc: AppError) -> dict:
    return {"status": status_for_error(exc), "error_code": exc.error_code, "message": exc.message}


def resolve_query_embedding(query_text: str, api_key: str | None) -> list[float] | None:
    try:
        return embed_query(query_text, api_key=api_key)
    except EmbeddingUnavailableError:
        return None


def run_hybrid_or_keyword_search(
    session: Session,
    query_text: str,
    top_k: int,
    *,
    api_key: str | None,
    project_id: str | None = None,
    boost_terms: list[str] | None = None,
    fetch_k: int = 20,
) -> tuple[list[RankedChunk], bool]:
    """Returns (ranked_chunks, embedding_used). Mirrors
    `rag/service.py::search_review_evidence`'s exact fallback: if no
    embedding is available (no GEMINI_API_KEY / a failed call), retrieval
    degrades to keyword-only rather than returning nothing."""
    from app.services.rag.retrieval import reciprocal_rank_fusion, rerank_with_keyword_boost

    query_embedding = resolve_query_embedding(query_text, api_key)

    if query_embedding is not None:
        ranked = hybrid_search(
            session,
            query_text,
            query_embedding,
            top_k=top_k,
            boost_terms=boost_terms,
            project_id=project_id,
            fetch_k=fetch_k,
        )
        return ranked, True

    keyword_results = keyword_search(session, query_text, fetch_k, project_id=project_id)
    fused = reciprocal_rank_fusion([], keyword_results)
    reranked = rerank_with_keyword_boost(fused, boost_terms or [])
    return reranked[:top_k], False
