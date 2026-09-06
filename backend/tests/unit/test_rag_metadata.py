from datetime import date

import pytest

from app.services.rag.metadata import detect_project_id, detect_sector, parse_edition_date


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("CompleteReviewReportAugust2025.pdf", date(2025, 8, 1)),
        ("CompleteReviewReportJuly2025.pdf", date(2025, 7, 1)),
        ("CompleteReviewReportJune2025.pdf", date(2025, 6, 1)),
        ("CompleteReviewReportMarch2025.pdf", date(2025, 3, 1)),
        ("Review Report Dec 25.pdf", date(2025, 12, 1)),
        ("Review Report Jan26.pdf", date(2026, 1, 1)),
        ("ReviewReportNov25.pdf", date(2025, 11, 1)),
        ("ReviewReportOct25.pdf", date(2025, 10, 1)),
        ("ReviewReportSep25.pdf", date(2025, 9, 1)),
    ],
)
def test_parse_edition_date_matches_real_filenames(filename: str, expected: date) -> None:
    assert parse_edition_date(filename) == expected


def test_parse_edition_date_no_match_returns_none() -> None:
    assert parse_edition_date("random_document.pdf") is None


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Power Generation (Non-renewable & Renewable)", "Power"),
        ("Coal including Lignite (Production)", "Coal"),
        ("Finished Steel (Production)", "Steel"),
        ("Roads (Up gradation of the highways by NHAI)", "Roads"),
        ("Railways (Passenger Traffic, Gauge)", "Railways"),
        ("Shipping & Ports (Cargo and Coal handled)", "Shipping & Ports"),
        ("Civil Aviation (Passenger traffic)", "Civil Aviation"),
        ("Telecommunications sector overview", "Telecommunications"),
        ("Production of Natural Gas increased", "Petroleum"),
    ],
)
def test_detect_sector_matches_documents_own_vocabulary(text: str, expected: str) -> None:
    assert detect_sector(text) == expected


def test_detect_sector_no_match_returns_none() -> None:
    assert detect_sector("This paragraph mentions nothing sector-related at all.") is None


def test_detect_sector_prefers_earliest_keyword() -> None:
    text = "This section briefly mentions ports before mainly discussing Power Generation targets."
    # "ports" appears before "power" in raw text, so it should win
    assert detect_sector(text) == "Shipping & Ports"


def test_detect_project_id_matches_project_name() -> None:
    lookup = {"development of keshod airport.": "619054", "powergrid": "617069"}
    text = "The Development of Keshod Airport. project reported progress this month."
    assert detect_project_id(text, lookup) == "619054"


def test_detect_project_id_no_match_returns_none_honestly() -> None:
    lookup = {"development of keshod airport.": "619054"}
    text = "This is a generic national infrastructure performance summary."
    assert detect_project_id(text, lookup) is None


def test_detect_project_id_prefers_longest_match() -> None:
    lookup = {"powergrid": "AGENCY", "powergrid koppal gadag": "616672"}
    text = "System strengthening by powergrid koppal gadag augmentation transmission limited."
    assert detect_project_id(text, lookup) == "616672"
