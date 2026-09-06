"""Integration tests for Document MCP (backend/app/mcp/documents/service.py).
pgvector genuinely does not exist outside Postgres (same rationale as
test_rag_vector_store.py), so this talks to the real configured database,
seeding a namespaced test document/chunks and always cleaning up."""

from __future__ import annotations

import math

import pytest

from app.core.db import SessionLocal, database_is_reachable
from app.models.document import Document, DocumentChunk

TEST_DOCUMENT_ID = "test-fixture-mcp-documents"
VALID_PROJECT_IDS = ["617069", "619054", "616672", "617184", "617279"]

pytestmark = pytest.mark.skipif(
    not database_is_reachable(), reason="requires a reachable Postgres with pgvector (Phase 7)"
)


def _unit_vector(seed: int, dim: int = 768) -> list[float]:
    values = [math.sin(seed * (i + 1) * 0.7) for i in range(dim)]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


@pytest.fixture
def db_session():
    session = SessionLocal()
    session.query(DocumentChunk).filter_by(document_id=TEST_DOCUMENT_ID).delete()
    session.query(Document).filter_by(document_id=TEST_DOCUMENT_ID).delete()
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.query(DocumentChunk).filter_by(document_id=TEST_DOCUMENT_ID).delete()
        session.query(Document).filter_by(document_id=TEST_DOCUMENT_ID).delete()
        session.commit()
        session.close()


def _seed_fixture(session) -> None:  # noqa: ANN001
    session.add(
        Document(
            document_id=TEST_DOCUMENT_ID, document_name="MCP Test Fixture Document",
            source_file="mcp_test_fixture.pdf", page_count=2,
        )
    )
    session.add_all(
        [
            DocumentChunk(
                document_id=TEST_DOCUMENT_ID, chunk_index=0, page=1,
                text="POWERGRID transmission project overview for MCP fixture.",
                char_count=10, extraction_method="TEXT", embedding=_unit_vector(1),
            ),
            DocumentChunk(
                document_id=TEST_DOCUMENT_ID, chunk_index=1, page=2,
                text="Second page of the MCP fixture document.",
                char_count=10, extraction_method="TEXT", embedding=_unit_vector(2),
            ),
        ]
    )
    session.commit()


def test_get_document_metadata(db_session) -> None:
    _seed_fixture(db_session)
    from app.mcp.documents.service import get_document_metadata

    result = get_document_metadata(TEST_DOCUMENT_ID)
    assert result.status == "OK"
    assert result.document_name == "MCP Test Fixture Document"
    assert result.chunk_count == 2


def test_get_document_metadata_not_found() -> None:
    from app.mcp.documents.service import get_document_metadata

    result = get_document_metadata("does-not-exist")
    assert result.status == "NOT_FOUND"


def test_retrieve_chunks_all_and_by_page(db_session) -> None:
    _seed_fixture(db_session)
    from app.mcp.documents.service import retrieve_chunks

    all_chunks = retrieve_chunks(TEST_DOCUMENT_ID)
    assert all_chunks.status == "OK"
    assert len(all_chunks.chunks) == 2

    page_1 = retrieve_chunks(TEST_DOCUMENT_ID, page=1)
    assert len(page_1.chunks) == 1
    assert page_1.chunks[0].page == 1


def test_get_document_page(db_session) -> None:
    _seed_fixture(db_session)
    from app.mcp.documents.service import get_document_page

    result = get_document_page(TEST_DOCUMENT_ID, page=1)
    assert result.status == "OK"
    assert "POWERGRID" in result.full_text


def test_get_document_page_not_available(db_session) -> None:
    _seed_fixture(db_session)
    from app.mcp.documents.service import get_document_page

    result = get_document_page(TEST_DOCUMENT_ID, page=99)
    assert result.status == "NOT_AVAILABLE"


def test_search_documents_finds_fixture_via_keyword_fallback(db_session) -> None:
    """Forces the no-embedding-available path (same contract as
    rag/service.py's own fallback) to confirm keyword-only search still
    finds the fixture, regardless of whether a real GEMINI_API_KEY happens
    to be configured in this environment."""
    from unittest.mock import patch

    from app.mcp.documents.service import search_documents

    _seed_fixture(db_session)
    with patch("app.mcp._shared.resolve_query_embedding", return_value=None):
        result = search_documents("POWERGRID transmission MCP fixture", top_k=5)

    assert result.status == "OK"
    assert result.embedding_used is False
    fixture_hits = [r for r in result.results if r.document_id == TEST_DOCUMENT_ID]
    assert len(fixture_hits) > 0


def test_find_project_mentions_for_all_five_projects() -> None:
    """Confirms Phase 7's own live finding still holds: the real corpus is
    national sector-aggregate bulletins, so retrieval always returns some
    sector-context chunks (evidence_found=True) even when no project is
    named directly - never a fabricated direct match."""
    from app.mcp.documents.service import find_project_mentions

    for project_id in VALID_PROJECT_IDS:
        result = find_project_mentions(project_id)
        assert result.status == "OK"
        assert result.answer
