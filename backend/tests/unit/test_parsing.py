from datetime import date

import pytest

from app.services.ingestion.parsing import (
    clean_str,
    extract_agency_code,
    parse_edition_month,
    parse_month_year,
    parse_numeric,
    parse_report_month,
)


@pytest.mark.parametrize("raw", ["", "-", "--", "NA", "na", "N/A", "  ", None])
def test_clean_str_treats_placeholders_as_missing(raw: str | None) -> None:
    assert clean_str(raw) is None


def test_clean_str_strips_whitespace() -> None:
    assert clean_str("  Gujarat  ") == "Gujarat"


def test_parse_numeric_missing() -> None:
    assert parse_numeric("-") is None
    assert parse_numeric("") is None


def test_parse_numeric_value() -> None:
    assert parse_numeric("466.00") == 466.0
    assert parse_numeric("1,354.00") == 1354.0


def test_parse_numeric_invalid_raises() -> None:
    with pytest.raises(ValueError):
        parse_numeric("not-a-number")


def test_parse_month_year() -> None:
    assert parse_month_year("02/2025") == date(2025, 2, 1)
    assert parse_month_year("") is None
    assert parse_month_year("-") is None


def test_parse_report_month() -> None:
    assert parse_report_month("2025-07") == date(2025, 7, 1)


def test_parse_edition_month() -> None:
    assert parse_edition_month("January 2026") == date(2026, 1, 1)
    assert parse_edition_month("July 2026") == date(2026, 7, 1)


def test_parse_edition_month_invalid() -> None:
    with pytest.raises(ValueError):
        parse_edition_month("Notamonth 2026")


def test_extract_agency_code() -> None:
    assert extract_agency_code("Power Grid Corporation of India Limited [POWERGRID]") == "POWERGRID"
    assert extract_agency_code("Airport Authority of India [AAI]") == "AAI"
    assert extract_agency_code(None) is None
    assert extract_agency_code("No brackets here") is None
