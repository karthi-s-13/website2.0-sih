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


def test_list_projects(client: TestClient) -> None:
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 5


def test_get_project_detail(client: TestClient) -> None:
    response = client.get("/api/v1/projects/617069")
    assert response.status_code == 200
    assert response.json()["data"]["project_id"] == "617069"


def test_get_project_detail_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/projects/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["errors"][0]["error_code"] == "NOT_FOUND"


def test_predict_endpoint_returns_expected_shape(client: TestClient) -> None:
    project = client.get("/api/v1/projects/617069").json()["data"]
    response = client.post(
        "/api/v1/projects/617069/predict",
        json={"prediction_date": project["latest_observation_month"]},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["project_id"] == "617069"
    assert data["risk_type"] == "cost_overrun"
    assert 0.0 <= data["probability"] <= 1.0
    assert data["risk_level"] in {"LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL"}
    assert data["model_version"].startswith("cost-overrun-lightgbm-")
    assert data["leakage_check"] == "PASSED"
    assert "feature_version" in data


def test_predict_endpoint_data_quality_failure(client: TestClient) -> None:
    response = client.post(
        "/api/v1/projects/617069/predict", json={"prediction_date": "2000-01-01"}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["errors"][0]["error_code"] == "DATA_QUALITY_FAILURE"


def test_get_model_info(client: TestClient) -> None:
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["model_type"] == "lightgbm"
    assert "optimal_threshold" in data
    assert "oof_metrics" in data
