"""Document MCP (Phase 12): review-report corpus search and retrieval
(Phase 7's `rag/` pipeline) - vector/keyword hybrid search, raw chunk/page
lookup, and document metadata. `find_project_mentions` reuses
`rag/service.py::search_review_evidence` wholesale (grounded Q&A with
citations - already the right shape).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.core.errors import AppError
from app.mcp._shared import run_hybrid_or_keyword_search, session_scope
from app.mcp.documents.schemas import (
    ChunkItem,
    ChunksResponse,
    CitationItem,
    DocumentMetadataResponse,
    DocumentPageChunk,
    DocumentPageResponse,
    ProjectMentionsResponse,
    SearchDocumentsResponse,
    SearchResultItem,
)
from app.repositories.document_repository import (
    count_chunks,
    get_chunks_by_indexes,
    get_chunks_by_page,
    get_document,
    list_chunks,
)
from app.services.rag.service import DEFAULT_QUESTION, search_review_evidence

mcp = FastMCP(
    "documents",
    instructions="Review-report corpus search and retrieval (Phase 7 RAG pipeline): "
    "hybrid search, raw chunk/page lookup, document metadata, project mentions.",
)

SNIPPET_LENGTH = 500


def _snippet(text: str) -> str:
    return text if len(text) <= SNIPPET_LENGTH else text[:SNIPPET_LENGTH] + "..."


@mcp.tool()
def search_documents(
    query: str, project_id: str | None = None, top_k: int = 5, sector: str | None = None
) -> SearchDocumentsResponse:
    """Hybrid (vector + keyword) search over the review-report corpus.
    `sector`, when given, is applied as a post-filter on the ranked results
    (no DB-level sector index exists) - may return fewer than top_k."""
    settings = get_settings()
    with session_scope() as session:
        ranked, embedding_used = run_hybrid_or_keyword_search(
            session, query, top_k * 3 if sector else top_k, api_key=settings.gemini_api_key, project_id=project_id
        )
        if sector:
            ranked = [r for r in ranked if r.chunk.sector == sector][:top_k]

        results = [
            SearchResultItem(
                chunk_id=r.chunk.id,
                document_id=r.chunk.document_id,
                document_name=r.chunk.document.document_name,
                page=r.chunk.page,
                text_snippet=_snippet(r.chunk.text),
                score=r.score,
                matched_vector=r.matched_vector,
                matched_keyword=r.matched_keyword,
                sector=r.chunk.sector,
                project_id=r.chunk.project_id,
            )
            for r in ranked
        ]
        return SearchDocumentsResponse(status="OK", query=query, embedding_used=embedding_used, results=results)


@mcp.tool()
def retrieve_chunks(
    document_id: str, chunk_indexes: list[int] | None = None, page: int | None = None
) -> ChunksResponse:
    """Raw chunks for a document: by explicit chunk_indexes, by page, or
    (if neither given) every chunk in the document."""
    with session_scope() as session:
        if get_document(session, document_id) is None:
            return ChunksResponse(status="NOT_FOUND", document_id=document_id)

        if chunk_indexes is not None:
            chunks = get_chunks_by_indexes(session, document_id, chunk_indexes)
        elif page is not None:
            chunks = get_chunks_by_page(session, document_id, page)
        else:
            chunks = list_chunks(session, document_id)

        items = [
            ChunkItem(
                chunk_index=c.chunk_index, page=c.page, text=c.text, char_count=c.char_count,
                extraction_method=c.extraction_method, sector=c.sector, project_id=c.project_id,
            )
            for c in chunks
        ]
        return ChunksResponse(status="OK", document_id=document_id, chunks=items)


@mcp.tool()
def get_document_page(document_id: str, page: int) -> DocumentPageResponse:
    """Full text of one page of a document, assembled from its chunks in
    order."""
    with session_scope() as session:
        document = get_document(session, document_id)
        if document is None:
            return DocumentPageResponse(status="NOT_FOUND", document_id=document_id, page=page)

        chunks = get_chunks_by_page(session, document_id, page)
        if not chunks:
            return DocumentPageResponse(
                status="NOT_AVAILABLE", document_id=document_id, document_name=document.document_name, page=page
            )

        items = [
            DocumentPageChunk(chunk_index=c.chunk_index, text=c.text, extraction_method=c.extraction_method)
            for c in chunks
        ]
        return DocumentPageResponse(
            status="OK",
            document_id=document_id,
            document_name=document.document_name,
            page=page,
            chunks=items,
            full_text="\n\n".join(c.text for c in chunks),
        )


@mcp.tool()
def get_document_metadata(document_id: str) -> DocumentMetadataResponse:
    """Metadata for one ingested review-report document."""
    with session_scope() as session:
        document = get_document(session, document_id)
        if document is None:
            return DocumentMetadataResponse(status="NOT_FOUND", document_id=document_id)

        return DocumentMetadataResponse(
            status="OK",
            document_id=document.document_id,
            document_name=document.document_name,
            source_file=document.source_file,
            edition_date=document.edition_date,
            source_type=document.source_type,
            page_count=document.page_count,
            ingested_at=document.ingested_at.isoformat() if document.ingested_at else None,
            chunk_count=count_chunks(session, document_id),
        )


@mcp.tool()
def find_project_mentions(project_id: str, question: str | None = None, top_k: int = 5) -> ProjectMentionsResponse:
    """Grounded Q&A over the review-report corpus for a specific project,
    with real (document_name, page) citations. Reuses Phase 7's own
    `search_review_evidence` wholesale - a batch retrieval-plus-LLM-answer
    call, not a raw text search."""
    with session_scope() as session:
        try:
            result = search_review_evidence(session, project_id, question=question or DEFAULT_QUESTION, top_k=top_k)
        except AppError as exc:
            status = "NOT_FOUND" if exc.error_code == "NOT_FOUND" else "NOT_AVAILABLE"
            return ProjectMentionsResponse(status=status, project_id=project_id, question=question)

        return ProjectMentionsResponse(
            status="OK",
            project_id=result.project_id,
            project_name=result.project_name,
            question=result.question,
            answer=result.answer,
            citations=[
                CitationItem(document_name=c.document_name, page=c.page, excerpt=c.excerpt, score=c.score)
                for c in result.citations
            ],
            evidence_found=result.evidence_found,
            summary_source=result.summary_source,
            summary_model=result.summary_model,
            searched_at=result.searched_at,
        )
