"""pgvector functionality genuinely does not exist outside Postgres, so -
unlike every other phase's tests - this file talks to the real configured
database (app.core.db.SessionLocal), not an in-memory SQLite fixture.
Requires a reachable Postgres with the Phase 7 migration applied.

Embeddings are synthetic fixed vectors (no real Gemini calls - keeps this
fast, free, and deterministic); rows are written under a clearly-namespaced
test document_id and always cleaned up in a `finally` block, whether the
test passes or fails.
"""

from __future__ import annotations

import math

import pytest
from sqlalchemy import text

from app.core.db import SessionLocal, database_is_reachable
from app.models.document import Document, DocumentChunk
from app.services.rag.retrieval import hybrid_search
from app.services.rag.vector_store import keyword_search, vector_search

TEST_DOCUMENT_ID = "test-fixture-rag-vector-store"

pytestmark = pytest.mark.skipif(
    not database_is_reachable(), reason="requires a reachable Postgres with pgvector (Phase 7)"
)


def _unit_vector(seed: int, dim: int = 768) -> list[float]:
    """A deterministic, roughly-orthogonal-ish unit vector per seed - good
    enough to produce distinguishable cosine distances for ordering tests."""
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


def _seed_fixture(session):
    session.add(
        Document(
            document_id=TEST_DOCUMENT_ID,
            document_name="Test Fixture Document",
            source_file="test_fixture.pdf",
            page_count=3,
        )
    )
    rows = [
        DocumentChunk(
            document_id=TEST_DOCUMENT_ID,
            chunk_index=0,
            page=1,
            text="POWERGRID transmission project performance overview.",
            char_count=10,
            extraction_method="TEXT",
            embedding=_unit_vector(1),
        ),
        DocumentChunk(
            document_id=TEST_DOCUMENT_ID,
            chunk_index=1,
            page=2,
            text="Unrelated content about telecommunications subscribers.",
            char_count=10,
            extraction_method="TEXT",
            embedding=_unit_vector(2),
        ),
        DocumentChunk(
            document_id=TEST_DOCUMENT_ID,
            chunk_index=2,
            page=3,
            text="Another mention of POWERGRID and transmission capacity.",
            char_count=10,
            extraction_method="TEXT",
            embedding=_unit_vector(3),
        ),
    ]
    session.add_all(rows)
    session.commit()
    return rows


def test_pgvector_extension_is_enabled(db_session) -> None:
    result = db_session.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchall()
    assert len(result) == 1


def test_vector_search_orders_by_cosine_distance(db_session) -> None:
    rows = _seed_fixture(db_session)
    query_embedding = _unit_vector(1)  # identical to the first chunk's embedding

    results = vector_search(db_session, query_embedding, top_k=3)
    result_ids = [chunk.id for chunk, _distance in results]

    assert rows[0].id in result_ids
    # the identical vector must be the closest match (distance ~0)
    assert results[0][0].id == rows[0].id
    assert results[0][1] < 0.001


def test_vector_search_respects_top_k(db_session) -> None:
    _seed_fixture(db_session)
    results = vector_search(db_session, _unit_vector(1), top_k=2)
    assert len(results) == 2


def test_keyword_search_finds_text_matches(db_session) -> None:
    _seed_fixture(db_session)
    results = keyword_search(db_session, "POWERGRID transmission", top_k=5)
    assert len(results) >= 2
    for chunk, _score in results:
        assert "powergrid" in chunk.text.lower() or "transmission" in chunk.text.lower()


def test_keyword_search_no_match_returns_empty(db_session) -> None:
    _seed_fixture(db_session)
    results = keyword_search(db_session, "xyznonexistentterm", top_k=5)
    assert results == []


def test_hybrid_search_returns_page_and_document_metadata(db_session) -> None:
    """Exit criterion groundwork: every retrieved chunk must carry the page
    number and (via the ORM relationship) the document name needed for a
    citation. The shared dev database may also hold real, already-ingested
    review-report chunks (Phase 7's own corpus) that legitimately match this
    query too - keyword_search is not document-scoped - so this only asserts
    metadata validity for every result, and separately confirms the seeded
    fixture chunk itself is retrievable among them."""
    _seed_fixture(db_session)
    ranked = hybrid_search(db_session, "POWERGRID transmission", _unit_vector(1), top_k=10)

    assert len(ranked) > 0
    for item in ranked:
        assert item.chunk.page > 0
        assert item.chunk.document.document_name

    fixture_hits = [item for item in ranked if item.chunk.document_id == TEST_DOCUMENT_ID]
    assert len(fixture_hits) > 0
    assert fixture_hits[0].chunk.page in {1, 2, 3}
    assert fixture_hits[0].chunk.document.document_name == "Test Fixture Document"
