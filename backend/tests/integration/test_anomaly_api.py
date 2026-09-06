from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base, get_db
from app.main import app
from app.services.ingestion.pipeline import ingest_directory

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"


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


def test_anomalies_endpoint_returns_shape(client: TestClient) -> None:
    response = client.get("/api/v1/projects/617069/anomalies")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["project_id"] == "617069"
    assert isinstance(data["anomalies"], list)
    assert "UNEXPECTED_MILESTONE_CHANGES" in data["unavailable_types"]


def test_anomalies_endpoint_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/projects/does-not-exist/anomalies")
    assert response.status_code == 404


def test_anomalies_endpoint_all_five_projects(client: TestClient) -> None:
    for project_id in ["617069", "619054", "616672", "617184", "617279"]:
        response = client.get(f"/api/v1/projects/{project_id}/anomalies")
        assert response.status_code == 200, response.text
