"""Integration tests for Analytics MCP (backend/app/mcp/analytics/service.py)
- confirms every per-metric wrapper's value matches the underlying
health/anomaly services exactly, over the real 5-project validation cohort
in a hermetic sqlite fixture."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.project import Project
from app.services.anomaly.service import get_project_anomalies
from app.services.health.formulas import HEALTH_FORMULA_VERSION
from app.services.health.service import get_project_health
from app.services.ingestion.pipeline import ingest_directory

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


def test_calculate_health_matches_get_project_health_exactly(mcp_session) -> None:
    from app.mcp.analytics.service import calculate_health

    for project_id in VALID_PROJECT_IDS:
        session = mcp_session()
        project = session.get(Project, project_id)
        expected = get_project_health(session, project_id, project.latest_observation_month)
        session.close()

        result = calculate_health(project_id)
        assert result.status == "OK"
        assert result.overall_health == expected.overall_health
        assert result.cost_utilisation == expected.cost_utilisation
        assert result.schedule_utilisation == expected.schedule_utilisation
        assert result.physical_progress == expected.physical_progress
        assert result.expected_progress == expected.expected_progress
        assert result.progress_gap == expected.progress_gap
        assert result.expenditure_progress_divergence == expected.expenditure_progress_divergence
        assert result.formula_version == HEALTH_FORMULA_VERSION


@pytest.mark.parametrize(
    "tool_name,health_field",
    [
        ("calculate_cost_utilisation", "cost_utilisation"),
        ("calculate_schedule_utilisation", "schedule_utilisation"),
        ("calculate_progress_gap", "progress_gap"),
        ("calculate_divergence", "expenditure_progress_divergence"),
        ("calculate_expected_progress", "expected_progress"),
    ],
)
def test_per_metric_wrapper_matches_health_vector_field(mcp_session, tool_name, health_field) -> None:
    import app.mcp.analytics.service as analytics_service

    tool = getattr(analytics_service, tool_name)

    for project_id in VALID_PROJECT_IDS:
        session = mcp_session()
        project = session.get(Project, project_id)
        expected = get_project_health(session, project_id, project.latest_observation_month)
        session.close()

        result = tool(project_id)
        assert result.status == "OK"
        assert result.value == getattr(expected, health_field)


def test_calculate_trend_returns_full_trend_object_not_scalar(mcp_session) -> None:
    from app.mcp.analytics.service import calculate_trend

    result = calculate_trend(VALID_PROJECT_IDS[0])
    assert result.status == "OK"
    assert isinstance(result.value, dict)
    assert "label" in result.value


def test_detect_anomaly_matches_underlying_service(mcp_session) -> None:
    from app.mcp.analytics.service import detect_anomaly

    for project_id in VALID_PROJECT_IDS:
        session = mcp_session()
        project = session.get(Project, project_id)
        expected = get_project_anomalies(session, project_id, project.latest_observation_month)
        session.close()

        result = detect_anomaly(project_id)
        assert result.status == "OK"
        assert len(result.anomalies) == len(expected.anomalies)
        assert result.unavailable_types == expected.unavailable_types
        assert result.input_observation_count == expected.input_observation_count


def test_not_found_for_all_metric_tools(mcp_session) -> None:
    import app.mcp.analytics.service as analytics_service

    for tool_name in [
        "calculate_health", "calculate_cost_utilisation", "calculate_schedule_utilisation",
        "calculate_progress_gap", "calculate_divergence", "calculate_expected_progress",
        "calculate_trend", "detect_anomaly",
    ]:
        result = getattr(analytics_service, tool_name)("does-not-exist")
        assert result.status == "NOT_FOUND"
