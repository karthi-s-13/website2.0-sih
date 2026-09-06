"""Uses the real Postgres database (pgvector requirement - see
test_rag_vector_store.py) with a real, already-ingested validation-cohort
project, plus synthetic test-only document chunks. Embeddings and the LLM
answer call are both mocked to keep this fast, free, and deterministic.
"""

from __future__ import annotations

import math
from unittest.mock import patch

import pytest

from app.core.db import SessionLocal, database_is_reachable
from app.core.errors import NotFoundError
from app.models.document import Document, DocumentChunk
from app.models.project import Project
from app.services.rag.answer import AnswerResult, Citation
from app.services.rag.service import search_review_evidence

TEST_DOCUMENT_ID = "test-fixture-rag-service"
REAL_PROJECT_ID = "617069"  # KPS1 - ingested by earlier phases' fixtures/scripts

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
    if session.get(Project, REAL_PROJECT_ID) is None:
        session.close()
        pytest.skip(f"project {REAL_PROJECT_ID} not ingested - run scripts/ingest_flash_reports.py first")

    session.query(DocumentChunk).filter_by(document_id=TEST_DOCUMENT_ID).delete()
    session.query(Document).filter_by(document_id=TEST_DOCUMENT_ID).delete()
    session.add(
        Document(
            document_id=TEST_DOCUMENT_ID,
            document_name="Test Fixture Review Report.pdf",
            source_file="test_fixture.pdf",
            page_count=1,
        )
    )
    session.add(
        DocumentChunk(
            document_id=TEST_DOCUMENT_ID,
            chunk_index=0,
            page=7,
            text="POWERGRID transmission projects showed steady progress this month.",
            char_count=10,
            extraction_method="TEXT",
            embedding=_unit_vector(42),
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.rollback()
        session.query(DocumentChunk).filter_by(document_id=TEST_DOCUMENT_ID).delete()
        session.query(Document).filter_by(document_id=TEST_DOCUMENT_ID).delete()
        session.commit()
        session.close()


FAKE_ANSWER = AnswerResult(
    text="Stubbed answer (Test Fixture Review Report.pdf, p.7).",
    source="LLM",
    model="gemini-3.6-flash",
    citations=[Citation(document_name="Test Fixture Review Report.pdf", page=7, excerpt="...", score=0.9)],
)


def test_search_review_evidence_returns_page_and_document_citations(db_session) -> None:
    """Exit criterion: retrieved answers contain document and page references."""
    with (
        patch("app.services.rag.service.embed_query", return_value=_unit_vector(42)),
        patch("app.services.rag.service.compose_answer", return_value=FAKE_ANSWER),
    ):
        result = search_review_evidence(db_session, REAL_PROJECT_ID, question="What does the report say?")

    assert result.project_id == REAL_PROJECT_ID
    assert result.evidence_found is True
    assert len(result.citations) > 0
    assert result.citations[0].document_name
    assert result.citations[0].page > 0


def test_search_review_evidence_unknown_project_raises(db_session) -> None:
    with pytest.raises(NotFoundError):
        search_review_evidence(db_session, "does-not-exist", question="q")


def test_search_review_evidence_embedding_unavailable_falls_back_to_keyword(db_session) -> None:
    from app.services.rag.embeddings import EmbeddingUnavailableError

    with (
        patch("app.services.rag.service.embed_query", side_effect=EmbeddingUnavailableError("no key")),
        patch("app.services.rag.service.compose_answer", return_value=FAKE_ANSWER),
    ):
        result = search_review_evidence(db_session, REAL_PROJECT_ID, question="POWERGRID transmission progress")

    # keyword search alone should still surface the seeded fixture chunk
    assert result.evidence_found is True
