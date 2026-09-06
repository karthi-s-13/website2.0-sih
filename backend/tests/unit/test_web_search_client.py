from unittest.mock import MagicMock, patch

import pytest

from app.services.web.search_client import WebSearchUnavailableError, search_web


def test_search_web_no_api_key_raises() -> None:
    with pytest.raises(WebSearchUnavailableError):
        search_web("some query", api_key=None)


def test_search_web_http_failure_raises() -> None:
    with patch("app.services.web.search_client.httpx.post", side_effect=RuntimeError("timeout")):
        with pytest.raises(WebSearchUnavailableError):
            search_web("some query", api_key="fake-key")


def test_search_web_parses_results_and_filters_non_https() -> None:
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "results": [
            {
                "title": "Bihar bridge project delayed",
                "url": "https://www.thehindu.com/article",
                "content": "Delay content.",
                "published_date": "2025-08-14",
            },
            {
                "title": "insecure result",
                "url": "http://insecure.example.com/article",
                "content": "should be dropped",
            },
        ]
    }
    with patch("app.services.web.search_client.httpx.post", return_value=fake_response):
        results = search_web("some query", api_key="fake-key")

    assert len(results) == 1
    assert results[0].url == "https://www.thehindu.com/article"
    assert results[0].published_date_raw == "2025-08-14"


def test_search_web_missing_url_uses_title_fallback() -> None:
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.json.return_value = {
        "results": [{"url": "https://example.com/x", "content": "content only"}]
    }
    with patch("app.services.web.search_client.httpx.post", return_value=fake_response):
        results = search_web("some query", api_key="fake-key")

    assert results[0].title == "https://example.com/x"
