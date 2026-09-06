from datetime import date

from app.services.web.date_verification import verify_date


def test_verify_date_none_input() -> None:
    parsed, confidence = verify_date(None)
    assert parsed is None
    assert confidence == "UNVERIFIED"


def test_verify_date_empty_string() -> None:
    parsed, confidence = verify_date("")
    assert parsed is None
    assert confidence == "UNVERIFIED"


def test_verify_date_iso_date() -> None:
    parsed, confidence = verify_date("2025-08-14")
    assert parsed == date(2025, 8, 14)
    assert confidence == "VERIFIED"


def test_verify_date_iso_datetime() -> None:
    parsed, confidence = verify_date("2025-08-14T10:30:00")
    assert parsed == date(2025, 8, 14)
    assert confidence == "VERIFIED"


def test_verify_date_iso_datetime_z() -> None:
    parsed, confidence = verify_date("2025-08-14T10:30:00Z")
    assert parsed == date(2025, 8, 14)
    assert confidence == "VERIFIED"


def test_verify_date_garbage_input() -> None:
    parsed, confidence = verify_date("sometime last year")
    assert parsed is None
    assert confidence == "UNVERIFIED"
