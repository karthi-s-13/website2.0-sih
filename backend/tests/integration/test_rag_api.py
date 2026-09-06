"""API-level test against the real configured database (pgvector requires
real Postgres - the sqlite dependency-override pattern used by other phases'
API tests does not apply here). Embeddings/LLM calls are mocked.
"""

from __future__ import annotations

import math
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.db import SessionLocal, database_is_reachable
from app.main import app
from app.models.document import Document, DocumentChunk
from app.models.project import Project
from app.services.rag.answer import AnswerResult, Citation

TEST_DOCUMENT_ID = "test-fixture-rag-api"
REAL_PROJECT_ID = "617069"

pytestmark = pytest.mark.skipif(
    not database_is_reachable(), reason="requires a reachable Postgres with pgvector (Phase 7)"
)


def _unit_vector(seed: int, dim: int = 768) -> list[float]:
    values = [math.sin(seed * (i + 1) * 0.7) for i in range(dim)]
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


@pytest.fixture
def seeded():
    session = SessionLocal()
    if session.get(Project, REAL_PROJECT_ID) is None:
        session.close()
        pytest.skip(f"project {REAL_PROJECT_ID} not ingested")

    session.query(DocumentChunk).filter_by(document_id=TEST_DOCUMENT_ID).delete()
    session.query(Document).filter_by(document_id=TEST_DOCUMENT_ID).delete()
    session.add(
        Document(
            document_id=TEST_DOCUMENT_ID,
            document_name="API Test Fixture Report.pdf",
            source_file="api_test_fixture.pdf",
            page_count=1,
        )
    )
    session.add(
        DocumentChunk(
            document_id=TEST_DOCUMENT_ID,
            chunk_index=0,
            page=9,
            text="POWERGRID transmission performance summary for API test.",
            char_count=10,
            extraction_method="TEXT",
            embedding=_unit_vector(99),
        )
    )
    session.commit()
    try:
        yield
    finally:
        session.rollback()
        session.query(DocumentChunk).filter_by(document_id=TEST_DOCUMENT_ID).delete()
        session.query(Document).filter_by(document_id=TEST_DOCUMENT_ID).delete()
        session.commit()
        session.close()


FAKE_ANSWER = AnswerResult(
    text="Stubbed API answer (API Test Fixture Report.pdf, p.9).",
    source="LLM",
    model="gemini-3.6-flash",
    citations=[Citation(document_name="API Test Fixture Report.pdf", page=9, excerpt="...", score=0.9)],
)


def test_review_evidence_endpoint_returns_citations(seeded) -> None:
    with (
        patch("app.services.rag.service.embed_query", return_value=_unit_vector(99)),
        patch("app.services.rag.service.compose_answer", return_value=FAKE_ANSWER),
    ):
        client = TestClient(app)
        response = client.get(f"/api/v1/projects/{REAL_PROJECT_ID}/review-evidence")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["project_id"] == REAL_PROJECT_ID
    assert data["evidence_found"] is True
    assert len(data["citations"]) > 0
    assert data["citations"][0]["document_name"]
    assert data["citations"][0]["page"] > 0


def test_review_evidence_endpoint_not_found() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/projects/does-not-exist/review-evidence")
    assert response.status_code == 404
