"""Integration tests for Web MCP (backend/app/mcp/web/service.py) - hermetic
by default (no TAVILY_API_KEY/GEMINI_API_KEY assumed), mirroring Phase 8's
own hermetic test pattern. One real-network test is opt-in only (env flag),
keeping the default suite fast and offline-safe."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest


def test_search_web_not_available_without_api_key() -> None:
    from app.mcp.web.service import search_web

    with patch("app.mcp.web.service.get_settings") as mock_settings:
        mock_settings.return_value.tavily_api_key = None
        result = search_web("infrastructure project delay")

    assert result.status == "NOT_AVAILABLE"
    assert result.warning is not None


def test_verify_source_classifies_tier_1_government_domain() -> None:
    from app.mcp.web.service import verify_source

    result = verify_source("https://powergrid.nic.in/press-release")
    assert result.status == "OK"
    assert result.trust_tier == "TIER_1"
    assert result.source_quality == "HIGH"


def test_verify_source_with_date_verification() -> None:
    from app.mcp.web.service import verify_source

    result = verify_source("https://example.com/x", published_date_raw="2025-06-01")
    assert result.published_date is not None
    assert result.date_confidence == "VERIFIED"


def test_verify_source_with_unparseable_date() -> None:
    from app.mcp.web.service import verify_source

    result = verify_source("https://example.com/x", published_date_raw="not-a-date")
    assert result.published_date is None
    assert result.date_confidence == "UNVERIFIED"


def test_extract_claim_falls_back_deterministically_without_api_key() -> None:
    from app.mcp.web.schemas import WebSearchResultItem
    from app.mcp.web.service import extract_claim

    with patch("app.mcp.web.service.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = None
        mock_settings.return_value.gemini_model = "gemini-3.6-flash"
        result = extract_claim(
            project_name="Test Project",
            topic="land acquisition",
            results=[
                WebSearchResultItem(
                    title="Some article", url="https://example.com/a",
                    content="This mentions Test Project delays.", published_date_raw=None,
                )
            ],
        )

    assert result.status == "OK"
    assert result.source == "DETERMINISTIC_FALLBACK"
    assert len(result.claims) == 1
    assert result.claims[0].url == "https://example.com/a"


@pytest.mark.skipif(
    os.environ.get("MCP_TEST_REAL_NETWORK") != "1",
    reason="opt-in real-network test - set MCP_TEST_REAL_NETWORK=1 to enable",
)
def test_fetch_source_real_network_call() -> None:
    from app.mcp.web.service import fetch_source

    result = fetch_source("https://example.com/")
    assert result.status == "OK"
    assert result.status_code == 200
    assert "Example Domain" in (result.content_text or "")
