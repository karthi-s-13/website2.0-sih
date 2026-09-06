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
from app.services.web.claim_extraction import ExtractedClaim
from app.services.web.search_client import SearchResult

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
FAKE_RESULTS = [
    SearchResult(
        title="Bihar bridge project delayed",
        url="https://www.thehindu.com/news/bridge-delay",
        content="A dispute was reported.",
        published_date_raw="2025-08-14",
    )
]


def _fake_claims(results, **kwargs):
    return [ExtractedClaim(result=r, finding="A dispute was reported.", project_relevance=0.7) for r in results]


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


def test_web_evidence_endpoint_not_triggered_by_default(client: TestClient) -> None:
    response = client.get("/api/v1/projects/617069/web-evidence")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["triggered"] is False
    assert data["evidence"] == []
    assert data["trigger_reason"]


def test_web_evidence_endpoint_force_returns_evidence(client: TestClient) -> None:
    with (
        patch("app.services.web.service.search_web", return_value=FAKE_RESULTS),
        patch("app.services.web.service.extract_claims", side_effect=_fake_claims),
    ):
        response = client.get("/api/v1/projects/617069/web-evidence", params={"force": "true"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["triggered"] is True
    assert len(data["evidence"]) > 0
    item = data["evidence"][0]
    assert item["url"] == "https://www.thehindu.com/news/bridge-delay"
    assert item["source_quality"] == "MEDIUM"
    assert item["project_relevance"] == 0.7


def test_web_evidence_endpoint_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/projects/does-not-exist/web-evidence")
    assert response.status_code == 404


def test_web_evidence_endpoint_all_five_projects(client: TestClient) -> None:
    with patch("app.services.web.service.search_web") as mock_search:
        for project_id in ["617069", "619054", "616672", "617184", "617279"]:
            response = client.get(f"/api/v1/projects/{project_id}/web-evidence")
            assert response.status_code == 200, response.text
    mock_search.assert_not_called()  # none of the 5 validation projects are HIGH/CRITICAL
