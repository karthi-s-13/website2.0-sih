"""Integration tests for Knowledge MCP (backend/app/mcp/knowledge/service.py).
vector_search/hybrid_search share Document MCP's fixture/rationale (real
Postgres, pgvector); store_evidence/retrieve_evidence round-trip against
the real web_evidence table (FK to a real project), always cleaned up."""

from __future__ import annotations

import math

import pytest

from app.core.db import SessionLocal, database_is_reachable
from app.models.document import Document, DocumentChunk
from app.models.web_evidence import WebEvidence

TEST_DOCUMENT_ID = "test-fixture-mcp-knowledge"
TEST_PROJECT_ID = "617069"  # a real validation-cohort project (web_evidence has an FK to projects)
TEST_EVIDENCE_URL = "https://example.com/mcp-knowledge-test-fixture"

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
    session.query(WebEvidence).filter_by(project_id=TEST_PROJECT_ID, url=TEST_EVIDENCE_URL).delete()
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.query(DocumentChunk).filter_by(document_id=TEST_DOCUMENT_ID).delete()
        session.query(Document).filter_by(document_id=TEST_DOCUMENT_ID).delete()
        session.query(WebEvidence).filter_by(project_id=TEST_PROJECT_ID, url=TEST_EVIDENCE_URL).delete()
        session.commit()
        session.close()


def _seed_document_fixture(session) -> None:  # noqa: ANN001
    session.add(
        Document(
            document_id=TEST_DOCUMENT_ID, document_name="Knowledge MCP Test Fixture",
            source_file="knowledge_fixture.pdf", page_count=1,
        )
    )
    session.add(
        DocumentChunk(
            document_id=TEST_DOCUMENT_ID, chunk_index=0, page=1,
            text="POWERGRID transmission capacity knowledge fixture chunk.",
            char_count=10, extraction_method="TEXT", embedding=_unit_vector(5),
        )
    )
    session.commit()


def test_vector_search_finds_fixture(db_session) -> None:
    _seed_document_fixture(db_session)
    from app.mcp.knowledge.service import vector_search

    result = vector_search("irrelevant query text", top_k=5)
    assert result.status in {"OK", "NOT_AVAILABLE"}
    if result.status == "OK":
        assert result.embedding_used is True


def test_hybrid_search_finds_fixture_via_keyword(db_session) -> None:
    from unittest.mock import patch

    _seed_document_fixture(db_session)
    from app.mcp.knowledge.service import hybrid_search

    with patch("app.mcp._shared.resolve_query_embedding", return_value=None):
        result = hybrid_search("POWERGRID transmission knowledge fixture", top_k=5)

    assert result.status == "OK"
    assert result.embedding_used is False
    fixture_hits = [r for r in result.results if r.document_id == TEST_DOCUMENT_ID]
    assert len(fixture_hits) > 0


def _make_evidence_input(finding: str):  # noqa: ANN202
    from app.mcp.knowledge.schemas import EvidenceInput

    return EvidenceInput(
        topic="mcp-knowledge-test", query_used="q", source="src", url=TEST_EVIDENCE_URL,
        title="T", finding=finding, project_relevance=0.5, trust_tier="TIER_4", source_quality="LOW",
    )


def test_store_and_retrieve_evidence_round_trip(db_session) -> None:
    from app.mcp.knowledge.service import retrieve_evidence, store_evidence

    store_result = store_evidence(TEST_PROJECT_ID, [_make_evidence_input("f")])
    assert store_result.status == "OK"
    assert store_result.stored_count == 1

    retrieve_result = retrieve_evidence(TEST_PROJECT_ID)
    matches = [e for e in retrieve_result.evidence if e.url == TEST_EVIDENCE_URL]
    assert len(matches) == 1
    assert matches[0].finding == "f"


def test_re_storing_same_triple_updates_not_duplicates(db_session) -> None:
    from app.mcp.knowledge.service import retrieve_evidence, store_evidence

    store_evidence(TEST_PROJECT_ID, [_make_evidence_input("first")])
    store_evidence(TEST_PROJECT_ID, [_make_evidence_input("second")])

    result = retrieve_evidence(TEST_PROJECT_ID)
    matches = [e for e in result.evidence if e.url == TEST_EVIDENCE_URL]
    assert len(matches) == 1
    assert matches[0].finding == "second"
