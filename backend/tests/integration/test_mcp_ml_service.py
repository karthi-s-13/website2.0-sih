"""Integration tests for ML MCP (backend/app/mcp/ml/service.py) against the
real model artifact + a hermetic sqlite fixture seeded with the real
5-project validation cohort."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.project import Project
from app.services.ingestion.pipeline import ingest_directory
from app.services.prediction.model_loader import load_model_bundle

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
VALID_PROJECT_IDS = ["617069", "619054", "616672", "617184", "617279"]


@pytest.fixture
def test_sessionmaker():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    ingest_directory(maker(), RAW_DIR)
    return maker


@pytest.fixture
def mcp_session(test_sessionmaker):
    with patch("app.mcp._shared.SessionLocal", test_sessionmaker):
        yield test_sessionmaker


def test_predict_cost_risk_valid_for_all_five_projects(mcp_session) -> None:
    from app.mcp.ml.service import predict_cost_risk

    for project_id in VALID_PROJECT_IDS:
        session = mcp_session()
        project = session.get(Project, project_id)
        session.close()

        result = predict_cost_risk(project_id, project.latest_observation_month)
        assert result.status == "OK"
        assert 0.0 <= result.probability <= 1.0
        assert result.risk_level in {"LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL"}
        assert result.leakage_check == "PASSED"


def test_predict_cost_risk_not_found(mcp_session) -> None:
    from datetime import date

    from app.mcp.ml.service import predict_cost_risk

    result = predict_cost_risk("does-not-exist", date(2026, 7, 1))
    assert result.status == "NOT_FOUND"


def test_predict_time_risk_always_not_available(mcp_session) -> None:
    from app.mcp.ml.service import predict_time_risk

    for project_id in VALID_PROJECT_IDS:
        session = mcp_session()
        project = session.get(Project, project_id)
        session.close()

        result = predict_time_risk(project_id, project.latest_observation_month)
        assert result.status == "NOT_AVAILABLE"
        assert "time-overrun" in result.reason.lower()


def test_get_model_metadata_matches_real_bundle() -> None:
    from app.mcp.ml.service import get_model_metadata

    bundle = load_model_bundle()
    result = get_model_metadata()
    assert result.status == "OK"
    assert result.model_version == bundle.model_version
    assert result.trained_at == bundle.trained_at
    assert result.raw_feature_cols == bundle.raw_feature_cols


def test_get_feature_schema_matches_model_columns() -> None:
    from pipeline.feature_engineering import FEATURE_COLUMNS

    from app.mcp.ml.service import get_feature_schema
    from app.services.features.pipeline import FEATURE_VERSION

    result = get_feature_schema()
    assert result.status == "OK"
    assert result.model_engineered_columns == FEATURE_COLUMNS
    assert result.phase2_feature_store_version == FEATURE_VERSION
    assert len(result.phase2_feature_store_fields) > 0


def test_explain_prediction_for_all_five_projects(mcp_session) -> None:
    from app.mcp.ml.service import explain_prediction

    for project_id in VALID_PROJECT_IDS:
        session = mcp_session()
        project = session.get(Project, project_id)
        session.close()

        result = explain_prediction(project_id, project.latest_observation_month)
        assert result.status == "OK"
        assert result.explanation_type in {"GLOBAL_FEATURE_IMPORTANCE", "NOT_AVAILABLE"}
        if result.explanation_type == "GLOBAL_FEATURE_IMPORTANCE":
            assert result.feature_importances
            assert result.feature_names_source in {
                "RECONSTRUCTED_FEATURE_COLUMNS", "MODEL_NATIVE", "ORDINAL_FALLBACK",
            }
            assert "SHAP" in result.caveat or "not a per-prediction" in result.caveat
