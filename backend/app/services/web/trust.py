"""Web source trust classification (spec section 21).

    TIER 1  Official government / statutory source        -> HIGH
    TIER 2  Official implementing agency / PSU source      -> HIGH
    TIER 3  Established news source                        -> MEDIUM
    TIER 4  Other secondary source                          -> LOW
    TIER 5  Unverified source (no resolvable domain)        -> UNVERIFIED

Unverified sources must never be treated as authoritative project facts -
`source_quality` is stored on every evidence row precisely so downstream
consumers can enforce that without re-deriving trust themselves.

The news-domain list is a deliberately small, curated set of established
Indian/international outlets - not exhaustive. Anything not recognised falls
through to TIER 4 rather than being guessed at.
"""

from __future__ import annotations

from urllib.parse import urlparse

TIER_1_SUFFIXES = (".gov.in", ".nic.in")

TIER_3_NEWS_DOMAINS = {
    "thehindu.com",
    "indianexpress.com",
    "timesofindia.indiatimes.com",
    "hindustantimes.com",
    "livemint.com",
    "business-standard.com",
    "ndtv.com",
    "moneycontrol.com",
    "economictimes.indiatimes.com",
    "financialexpress.com",
    "reuters.com",
    "pti.in",
    "downtoearth.org.in",
    "thewire.in",
    "scroll.in",
}

TRUST_TIER_TO_QUALITY = {
    "TIER_1": "HIGH",
    "TIER_2": "HIGH",
    "TIER_3": "MEDIUM",
    "TIER_4": "LOW",
    "TIER_5": "UNVERIFIED",
}


def extract_domain(url: str) -> str | None:
    try:
        netloc = urlparse(url).netloc.lower()
    except ValueError:
        return None
    if not netloc:
        return None
    return netloc[4:] if netloc.startswith("www.") else netloc


def classify_source(url: str, agency_code: str | None = None) -> tuple[str, str]:
    """Returns (trust_tier, source_quality)."""
    domain = extract_domain(url)
    if not domain:
        return "TIER_5", TRUST_TIER_TO_QUALITY["TIER_5"]

    if domain.endswith(TIER_1_SUFFIXES):
        return "TIER_1", TRUST_TIER_TO_QUALITY["TIER_1"]

    if agency_code and agency_code.lower() in domain:
        return "TIER_2", TRUST_TIER_TO_QUALITY["TIER_2"]

    if domain in TIER_3_NEWS_DOMAINS:
        return "TIER_3", TRUST_TIER_TO_QUALITY["TIER_3"]

    return "TIER_4", TRUST_TIER_TO_QUALITY["TIER_4"]
