"""Integration tests for PAIMANA MCP (backend/app/mcp/paimana/service.py)
against a hermetic in-memory sqlite DB seeded with the real 5-project
validation cohort - same fixture pattern as test_intervention_service.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
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
        yield


def test_get_project_for_all_five_projects(mcp_session) -> None:
    from app.mcp.paimana.service import get_project

    for project_id in VALID_PROJECT_IDS:
        result = get_project(project_id)
        assert result.status == "OK"
        assert result.project_id == project_id
        assert result.project_name


def test_get_project_not_found(mcp_session) -> None:
    from app.mcp.paimana.service import get_project

    result = get_project("does-not-exist")
    assert result.status == "NOT_FOUND"
    assert result.project_id == "does-not-exist"


def test_get_monthly_observations_for_all_five_projects(mcp_session) -> None:
    from app.mcp.paimana.service import get_monthly_observations

    for project_id in VALID_PROJECT_IDS:
        result = get_monthly_observations(project_id)
        assert result.status == "OK"
        assert result.count > 0
        assert result.count == len(result.observations)


def test_get_monthly_observations_date_filter(mcp_session) -> None:
    from app.mcp.paimana.service import get_monthly_observations

    unfiltered = get_monthly_observations(VALID_PROJECT_IDS[0])
    months = sorted(o.observation_month for o in unfiltered.observations)
    assert len(months) >= 2

    filtered = get_monthly_observations(VALID_PROJECT_IDS[0], start_date=months[1])
    assert all(o.observation_month >= months[1] for o in filtered.observations)
    assert filtered.count < unfiltered.count


def test_get_milestones_honestly_unavailable_never_an_error(mcp_session) -> None:
    """The real Flash Report source data has no milestone fields - this
    must return OK + empty + unavailable=True, never an error."""
    from app.mcp.paimana.service import get_milestones

    for project_id in VALID_PROJECT_IDS:
        result = get_milestones(project_id)
        assert result.status == "OK"
        assert result.unavailable is True
        assert result.milestones == []


def test_get_project_events_for_all_five_projects(mcp_session) -> None:
    from app.mcp.paimana.service import get_project_events

    for project_id in VALID_PROJECT_IDS:
        result = get_project_events(project_id)
        assert result.status == "OK"
        assert result.count == len(result.events)


def test_non_project_tools_distinguish_not_found_from_empty(mcp_session) -> None:
    from app.mcp.paimana.service import get_milestones, get_monthly_observations, get_project_events

    for fn in (get_monthly_observations, get_milestones, get_project_events):
        result = fn("does-not-exist")
        assert result.status == "NOT_FOUND"
