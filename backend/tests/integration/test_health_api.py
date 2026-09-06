from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base, get_db
from app.main import app
from app.services.health.formulas import HEALTH_LEVELS
from app.services.ingestion.pipeline import ingest_directory

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
VALID_PROJECT_IDS = ["617069", "619054", "616672", "617184", "617279"]


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


def test_health_endpoint_defaults_to_latest_month(client: TestClient) -> None:
    response = client.get("/api/v1/projects/617069/health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["project_id"] == "617069"
    assert data["overall_health"] in {*HEALTH_LEVELS, "DATA_NOT_AVAILABLE"}
    assert "recent_trend" in data
    assert "milestone_health" in data
    assert data["milestone_health"]["status"] == "NOT_AVAILABLE"


def test_health_endpoint_for_all_five_projects(client: TestClient) -> None:
    """Exit criterion, exercised over the real HTTP API."""
    for project_id in VALID_PROJECT_IDS:
        response = client.get(f"/api/v1/projects/{project_id}/health")
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["overall_health"] in {*HEALTH_LEVELS, "DATA_NOT_AVAILABLE"}


def test_health_endpoint_accepts_as_of_query_param(client: TestClient) -> None:
    response = client.get("/api/v1/projects/617069/health?as_of=2025-07-01")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["snapshot_month"] == "2025-07-01"


def test_health_endpoint_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/projects/does-not-exist/health")
    assert response.status_code == 404


def test_health_endpoint_data_quality_failure_for_early_date(client: TestClient) -> None:
    response = client.get("/api/v1/projects/617069/health?as_of=2000-01-01")
    assert response.status_code == 422
    assert response.json()["errors"][0]["error_code"] == "DATA_QUALITY_FAILURE"
