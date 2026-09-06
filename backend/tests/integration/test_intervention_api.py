from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base, get_db
from app.main import app
from app.services.ingestion.pipeline import ingest_directory
from app.services.rag.service import EvidenceResult
from app.services.web.service import WebIntelligenceResult

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"

NOT_FOUND_REVIEW = EvidenceResult(
    project_id="x", project_name="x", question="q", answer="not mentioned", citations=[],
    summary_source="DETERMINISTIC_FALLBACK", summary_model=None, evidence_found=False,
    searched_at="2026-07-01T00:00:00Z",
)
NOT_TRIGGERED_WEB = WebIntelligenceResult(
    project_id="x", project_name="x", triggered=False, trigger_reason="not high risk",
    topics_searched=[], evidence=[], warnings=[], searched_at="2026-07-01T00:00:00Z",
)


@pytest.fixture
def client() -> TestClient:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    test_session_factory = sessionmaker(bind=engine)

    with Session(engine) as setup_session:
        ingest_directory(setup_session, RAW_DIR)

    def override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_interventions_endpoint_returns_expected_shape(client: TestClient) -> None:
    with (
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
    ):
        response = client.get("/api/v1/projects/617069/interventions")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["project_id"] == "617069"
    assert data["suggested_monitoring_level"] in {"NORMAL", "ENHANCED", "PRIORITY", "CRITICAL"}
    for rec in data["recommendations"]:
        assert set(rec.keys()) >= {"priority", "action", "reason", "evidence_ids"}
        assert rec["action"]
        assert rec["reason"]


def test_interventions_endpoint_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/projects/does-not-exist/interventions")
    assert response.status_code == 404


def test_interventions_endpoint_all_five_projects(client: TestClient) -> None:
    with (
        patch("app.services.diagnosis.service.search_review_evidence", return_value=NOT_FOUND_REVIEW),
        patch("app.services.diagnosis.service.get_web_intelligence", return_value=NOT_TRIGGERED_WEB),
    ):
        for project_id in ["617069", "619054", "616672", "617184", "617279"]:
            response = client.get(f"/api/v1/projects/{project_id}/interventions")
            assert response.status_code == 200, response.text
