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
from app.services.history.llm import SummaryResult
from app.services.ingestion.pipeline import ingest_directory

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
FAKE_SUMMARY = SummaryResult(text="stubbed narrative summary", source="LLM", model="gemini-3.6-flash")


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


def test_history_endpoint_default_question(client: TestClient) -> None:
    with patch("app.services.history.service.summarize_current_state", return_value=FAKE_SUMMARY):
        response = client.get("/api/v1/projects/617069/history")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["project_id"] == "617069"
    assert data["question"] == "What happened to this project?"
    assert data["current_state"] == "stubbed narrative summary"
    assert len(data["timeline"]) > 0
    assert all(entry["source_type"] for entry in data["timeline"])


def test_history_endpoint_custom_question(client: TestClient) -> None:
    with patch("app.services.history.service.summarize_current_state", return_value=FAKE_SUMMARY):
        response = client.get(
            "/api/v1/projects/617069/history", params={"question": "Why is this risky?"}
        )
    assert response.status_code == 200
    assert response.json()["data"]["question"] == "Why is this risky?"


def test_history_endpoint_not_found(client: TestClient) -> None:
    with patch("app.services.history.service.summarize_current_state", return_value=FAKE_SUMMARY):
        response = client.get("/api/v1/projects/does-not-exist/history")
    assert response.status_code == 404


def test_history_endpoint_all_five_projects(client: TestClient) -> None:
    with patch("app.services.history.service.summarize_current_state", return_value=FAKE_SUMMARY):
        for project_id in ["617069", "619054", "616672", "617184", "617279"]:
            response = client.get(f"/api/v1/projects/{project_id}/history")
            assert response.status_code == 200, response.text
