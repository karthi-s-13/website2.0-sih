"""Tavily search client (Web MCP spec section 40: search_web tool).

Enforces the MCP's required policies directly at the HTTP boundary:
timeout, a hard cap on results (rate-limit/budget discipline), and HTTPS-only
URLs (URL safety) - trust-tier domain policy itself lives in `trust.py` and
is applied by the caller so a low-trust result is still surfaced (with its
tier attached), never silently dropped here.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
REQUEST_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_RESULTS = 5


class WebSearchUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    content: str
    published_date_raw: str | None


def search_web(
    query: str, *, api_key: str | None, max_results: int = DEFAULT_MAX_RESULTS
) -> list[SearchResult]:
    if not api_key:
        raise WebSearchUnavailableError("TAVILY_API_KEY is not configured.")

    try:
        response = httpx.post(
            TAVILY_SEARCH_URL,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": False,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 - any failure must degrade gracefully upstream
        raise WebSearchUnavailableError(f"web search request failed: {exc}") from exc

    results = []
    for item in payload.get("results", []):
        url = item.get("url") or ""
        if not url.lower().startswith("https://"):
            continue  # URL safety: only accept https sources
        results.append(
            SearchResult(
                title=item.get("title") or url,
                url=url,
                content=item.get("content") or "",
                published_date_raw=item.get("published_date"),
            )
        )
    return results
