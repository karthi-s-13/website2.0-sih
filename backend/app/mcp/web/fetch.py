"""Safe, bounded URL fetch for Web MCP's `fetch_source` tool (spec section
40: URL safety, timeout, domain policies, rate limits).

This is genuinely new, security-sensitive code - no other module in this
codebase fetches an arbitrary caller-given URL (Tavily's own server-side
fetch already backs `search_web`; `httpx` is otherwise only ever used
against fixed, trusted endpoints - Tavily, Gemini).

Checks, in order:
  1. scheme must be http/https.
  2. every DNS-resolved address for the hostname is checked against
     private/loopback/link-local/reserved/multicast/unspecified ranges -
     by IP range, not by string-matching "localhost" (blocks 127.0.0.1,
     10.0.0.0/8, 169.254.169.254 cloud metadata, ::1, etc.).
  3. redirects are never followed automatically - a 3xx response is
     returned to the caller as its own result (status="REDIRECT"), who
     must re-invoke this function with the new URL so it is independently
     re-validated from step 1. This closes the classic SSRF-via-redirect
     bypass by construction.
  4. the response body is streamed with a hard byte cap.
  5. a timeout covers the whole request.

Documented, accepted limitation (same spirit as `web/trust.py`'s curated
TIER_3 domain list - not exhaustive, stated rather than glossed over): this
is pre-flight DNS validation, not a fully pinned-connection transport - a
DNS-rebinding attacker who changes the DNS answer between the
`getaddrinfo` check below and httpx's own connection could theoretically
still reach a private address. Given this project's stated minimal-new-
infra preference and the low-value target here (fetching a handful of URLs
already surfaced by a search engine), this is an accepted trade-off, not an
oversight.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

ALLOWED_SCHEMES = {"http", "https"}
DEFAULT_MAX_BYTES = 200_000
DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class FetchResult:
    status: str  # OK | REJECTED | REDIRECT | ERROR
    final_url: str
    status_code: int | None
    content_type: str | None
    content_text: str | None
    truncated: bool
    redirect_location: str | None
    rejected_reason: str | None
    message: str | None


def _is_unsafe_ip(ip_str: str) -> bool:
    ip = ipaddress.ip_address(ip_str)
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _rejected(url: str, reason: str, message: str) -> FetchResult:
    return FetchResult(
        status="REJECTED", final_url=url, status_code=None, content_type=None, content_text=None,
        truncated=False, redirect_location=None, rejected_reason=reason, message=message,
    )


def safe_fetch(
    url: str, max_bytes: int = DEFAULT_MAX_BYTES, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
) -> FetchResult:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return _rejected(url, "UNSAFE_SCHEME", f"scheme {parsed.scheme!r} is not http/https")

    hostname = parsed.hostname
    if not hostname:
        return _rejected(url, "UNSAFE_HOST", "URL has no resolvable hostname")

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        return _rejected(url, "DNS_RESOLUTION_FAILED", str(exc))

    resolved_ips = {info[4][0] for info in addrinfo}
    for ip_str in resolved_ips:
        try:
            if _is_unsafe_ip(ip_str):
                return _rejected(url, "UNSAFE_HOST", f"{hostname} resolves to disallowed address {ip_str}")
        except ValueError:
            return _rejected(url, "UNSAFE_HOST", f"{hostname} resolved to an unparseable address {ip_str}")

    try:
        with httpx.stream("GET", url, timeout=timeout_seconds, follow_redirects=False) as response:
            if response.is_redirect:
                return FetchResult(
                    status="REDIRECT", final_url=url, status_code=response.status_code,
                    content_type=response.headers.get("content-type"), content_text=None, truncated=False,
                    redirect_location=response.headers.get("location"), rejected_reason=None, message=None,
                )

            chunks: list[bytes] = []
            total = 0
            truncated = False
            for chunk in response.iter_bytes():
                remaining = max_bytes - total
                if remaining <= 0:
                    truncated = True
                    break
                chunks.append(chunk[:remaining])
                total += len(chunk[:remaining])
                if len(chunk) > remaining:
                    truncated = True
                    break

            body = b"".join(chunks)
            content_text = body.decode(response.encoding or "utf-8", errors="replace")

            return FetchResult(
                status="OK", final_url=str(response.url), status_code=response.status_code,
                content_type=response.headers.get("content-type"), content_text=content_text,
                truncated=truncated, redirect_location=None, rejected_reason=None, message=None,
            )
    except httpx.HTTPError as exc:
        return FetchResult(
            status="ERROR", final_url=url, status_code=None, content_type=None, content_text=None,
            truncated=False, redirect_location=None, rejected_reason=None, message=str(exc),
        )
