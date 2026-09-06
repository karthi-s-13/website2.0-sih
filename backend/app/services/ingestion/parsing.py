"""Pure, side-effect-free parsing/normalization helpers for raw Flash Report cells.

Kept dependency-free (no DB, no pandas) so they are trivial to unit test.
"""

from __future__ import annotations

from datetime import date

MISSING_TOKENS = {"", "-", "--", "na", "n/a", "nil", "none"}


def clean_str(value: object) -> str | None:
    """Strip whitespace and normalize placeholder tokens ("-", "NA", "") to None."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in MISSING_TOKENS:
        return None
    return text


def parse_numeric(value: object) -> float | None:
    """Parse a numeric cell (crore/percent values). Returns None for missing values.

    Raises ValueError if the value is present but not a valid number, so the
    caller can distinguish "legitimately missing" from "malformed".
    """
    text = clean_str(value)
    if text is None:
        return None
    text = text.replace(",", "")
    return float(text)


def parse_month_year(value: object) -> date | None:
    """Parse an "MM/YYYY" cell (date_of_approval, start_date, target/revised
    completion date) into a date on the 1st of that month. Source data has no
    day-level precision, so day=1 is a normalization convention, not a claim
    of a specific day.
    """
    text = clean_str(value)
    if text is None:
        return None
    month_str, _, year_str = text.partition("/")
    if not year_str:
        raise ValueError(f"expected MM/YYYY, got {value!r}")
    month, year = int(month_str), int(year_str)
    return date(year, month, 1)


def parse_report_month(value: object) -> date | None:
    """Parse a "YYYY-MM" report_month cell into a date on the 1st of that month."""
    text = clean_str(value)
    if text is None:
        return None
    year_str, _, month_str = text.partition("-")
    if not month_str:
        raise ValueError(f"expected YYYY-MM, got {value!r}")
    return date(int(year_str), int(month_str), 1)


_MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def parse_edition_month(value: object) -> date | None:
    """Parse an "edition" cell like "January 2026" into a date on the 1st of that month."""
    text = clean_str(value)
    if text is None:
        return None
    month_str, _, year_str = text.rpartition(" ")
    month_num = _MONTH_NAMES.get(month_str.strip().lower())
    if month_num is None or not year_str:
        raise ValueError(f"expected 'Month YYYY', got {value!r}")
    return date(int(year_str), month_num, 1)


def extract_agency_code(agency: str | None) -> str | None:
    """Extract a trailing bracketed abbreviation, e.g. "...[POWERGRID]" -> "POWERGRID"."""
    if not agency:
        return None
    start = agency.rfind("[")
    end = agency.rfind("]")
    if start == -1 or end == -1 or end < start:
        return None
    code = agency[start + 1 : end].strip()
    return code or None
