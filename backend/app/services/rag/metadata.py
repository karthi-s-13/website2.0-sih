"""Chunk metadata (Phase 7 pipeline stage 4): document_id, document_name,
page, project_id, date, ministry, sector, source_type.

`sector` is a best-effort heuristic, not authoritative: the real review
reports are national sector-aggregate bulletins that name their own eleven
components explicitly (confirmed by inspecting the documents' own
"Introduction" section) - that stated list, not a guess, is the keyword
vocabulary used here. `project_id` is left null unless a project's own name/
agency/state literally appears in the chunk text - these are national
reports, not project-level write-ups, so most chunks will have no project
match, and that is reported honestly rather than forced.

`ministry` is deliberately NOT set from these documents: no letterhead/ministry
name was found in the extracted text or PDF metadata of the actual files (the
cover page is an unlabeled image). Inventing "MoSPI" would be a fabricated
field value, not a recovered fact - see docs/model_integration_notes.md for
the same evidence-over-inference principle applied to the ML model.
"""

from __future__ import annotations

import re
from datetime import date

# The exact eleven components the review reports state they cover (see
# "Introduction" section of the real PDFs) - not invented.
SECTOR_KEYWORDS: list[tuple[str, str]] = [
    ("power", "Power"),
    ("coal", "Coal"),
    ("steel", "Steel"),
    ("cement", "Cement"),
    ("fertilizer", "Fertilizers"),
    ("petroleum", "Petroleum"),
    ("natural gas", "Petroleum"),
    ("crude oil", "Petroleum"),
    ("road", "Roads"),
    ("highway", "Roads"),
    ("railway", "Railways"),
    ("shipping", "Shipping & Ports"),
    ("port", "Shipping & Ports"),
    ("civil aviation", "Civil Aviation"),
    ("aircraft", "Civil Aviation"),
    ("telecom", "Telecommunications"),
]

_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}  # fmt: skip

_DATE_PATTERN = re.compile(
    r"(?P<month>" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\s*(?P<year>\d{2,4})",
    re.IGNORECASE,
)


def parse_edition_date(filename: str) -> date | None:
    """Parses a review-report filename like "CompleteReviewReportAugust2025.pdf"
    or "Review Report Dec 25.pdf" into the 1st of that edition month."""
    match = _DATE_PATTERN.search(filename)
    if not match:
        return None
    month = _MONTHS[match.group("month").lower()]
    year_str = match.group("year")
    year = int(year_str)
    if len(year_str) == 2:
        year += 2000
    return date(year, month, 1)


def detect_sector(text: str) -> str | None:
    lowered = text.lower()
    best: tuple[int, str] | None = None
    for keyword, canonical in SECTOR_KEYWORDS:
        pos = lowered.find(keyword)
        if pos != -1 and (best is None or pos < best[0]):
            best = (pos, canonical)
    return best[1] if best else None


def detect_project_id(text: str, project_lookup: dict[str, str]) -> str | None:
    """project_lookup maps a searchable phrase (project name, agency code,
    state name - already lowercased) to project_id. Returns the first match,
    preferring the longest/most specific phrase."""
    lowered = text.lower()
    matches = [(len(phrase), pid) for phrase, pid in project_lookup.items() if phrase in lowered]
    if not matches:
        return None
    return max(matches, key=lambda m: m[0])[1]
