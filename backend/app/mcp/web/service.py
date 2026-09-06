"""Web MCP (Phase 12): external web search, source fetch/verification, and
claim extraction (Phase 8's Web Intelligence Agent building blocks).
`extract_claim` is batch-shaped (matches the real backing function's
contract) despite its singular tool name.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.mcp.web.fetch import DEFAULT_MAX_BYTES, DEFAULT_TIMEOUT_SECONDS, safe_fetch
from app.mcp.web.schemas import (
    ClaimItem,
    ExtractClaimResponse,
    FetchSourceResponse,
    SearchWebResponse,
    VerifySourceResponse,
    WebSearchResultItem,
)
from app.services.web import trust
from app.services.web.claim_extraction import _deterministic_claims, extract_claims
from app.services.web.date_verification import verify_date
from app.services.web.search_client import SearchResult, WebSearchUnavailableError
from app.services.web.search_client import search_web as _search_web

mcp = FastMCP(
    "web",
    instructions="External web search (Tavily), safe URL fetch, source trust "
    "verification, and claim extraction - Phase 8's Web Intelligence Agent building blocks.",
)


@mcp.tool()
def search_web(query: str, max_results: int = 5) -> SearchWebResponse:
    """Web search via Tavily (advanced search_depth, HTTPS-only results).
    Returns status="NOT_AVAILABLE" with a warning (never raises) if
    TAVILY_API_KEY is not configured or the request fails."""
    settings = get_settings()
    try:
        results = _search_web(query, api_key=settings.tavily_api_key, max_results=max_results)
    except WebSearchUnavailableError as exc:
        return SearchWebResponse(status="NOT_AVAILABLE", query=query, warning=str(exc))

    return SearchWebResponse(
        status="OK",
        query=query,
        results=[
            WebSearchResultItem(title=r.title, url=r.url, content=r.content, published_date_raw=r.published_date_raw)
            for r in results
        ],
    )


@mcp.tool()
def fetch_source(
    url: str, max_bytes: int = DEFAULT_MAX_BYTES, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
) -> FetchSourceResponse:
    """Fetches a URL directly, with SSRF-safe pre-flight validation (scheme
    check, DNS-resolved-IP range check against private/loopback/link-local/
    reserved/multicast ranges), no automatic redirect following (a 3xx is
    returned as status="REDIRECT" for the caller to re-validate from
    scratch), and a hard byte cap on the streamed response body. See
    app/mcp/web/fetch.py's module docstring for the full policy and its one
    documented, accepted limitation (pre-flight DNS validation, not a fully
    pinned-connection transport)."""
    result = safe_fetch(url, max_bytes=max_bytes, timeout_seconds=timeout_seconds)
    return FetchSourceResponse(
        status=result.status,
        url=url,
        final_url=result.final_url,
        status_code=result.status_code,
        content_type=result.content_type,
        content_text=result.content_text,
        truncated=result.truncated,
        redirect_location=result.redirect_location,
        rejected_reason=result.rejected_reason,
        message=result.message,
    )


@mcp.tool()
def verify_source(
    url: str, agency_code: str | None = None, published_date_raw: str | None = None
) -> VerifySourceResponse:
    """Classifies a URL's trust tier (TIER_1..TIER_5, Phase 8's own domain
    policy) and, if a raw published-date string is given, verifies it."""
    trust_tier, source_quality = trust.classify_source(url, agency_code)
    domain = trust.extract_domain(url)

    published_date = date_confidence = None
    if published_date_raw is not None:
        published_date, date_confidence = verify_date(published_date_raw)

    return VerifySourceResponse(
        status="OK",
        url=url,
        domain=domain,
        trust_tier=trust_tier,
        source_quality=source_quality,
        published_date=published_date,
        date_confidence=date_confidence,
    )


@mcp.tool()
def extract_claim(
    project_name: str,
    topic: str,
    results: list[WebSearchResultItem],
    agency: str | None = None,
    state: str | None = None,
) -> ExtractClaimResponse:
    """Extracts one factual finding + project-relevance score per search
    result (batch call - `results` is a list, matching the backing
    function's real contract despite the singular tool name). Falls back to
    a deterministic snippet + keyword-overlap extraction with no
    GEMINI_API_KEY, a failed call, or invalid/mismatched LLM output - never
    invents a finding not grounded in the given content."""
    settings = get_settings()
    search_results = [
        SearchResult(title=r.title, url=r.url, content=r.content, published_date_raw=r.published_date_raw)
        for r in results
    ]

    claims = extract_claims(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        project_name=project_name,
        agency=agency,
        state=state,
        topic=topic,
        results=search_results,
    )

    # extract_claims doesn't expose whether it used the LLM or its internal
    # fallback - deterministic fallback output is a pure function of the
    # inputs, so an exact match against it (recomputed here for comparison
    # only, not reused as the actual extraction) reliably distinguishes the
    # two paths without duplicating claim_extraction.py's real logic.
    fallback = _deterministic_claims(search_results, project_name, agency, state)
    used_fallback = [(c.finding, c.project_relevance) for c in claims] == [
        (c.finding, c.project_relevance) for c in fallback
    ]

    claim_items = []
    for claim in claims:
        trust_tier, source_quality = trust.classify_source(claim.result.url, agency)
        claim_items.append(
            ClaimItem(
                url=claim.result.url, title=claim.result.title, finding=claim.finding,
                project_relevance=claim.project_relevance, trust_tier=trust_tier, source_quality=source_quality,
            )
        )

    return ExtractClaimResponse(
        status="OK",
        topic=topic,
        source="DETERMINISTIC_FALLBACK" if used_fallback else "LLM",
        claims=claim_items,
    )
