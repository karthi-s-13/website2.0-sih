from app.services.web.trust import classify_source, extract_domain


def test_extract_domain_strips_www() -> None:
    assert extract_domain("https://www.thehindu.com/some/article") == "thehindu.com"


def test_extract_domain_no_www() -> None:
    assert extract_domain("https://pib.gov.in/press") == "pib.gov.in"


def test_extract_domain_invalid_url() -> None:
    assert extract_domain("not a url") is None


def test_tier_1_government_domain() -> None:
    tier, quality = classify_source("https://morth.nic.in/notice")
    assert tier == "TIER_1"
    assert quality == "HIGH"


def test_tier_1_gov_in_domain() -> None:
    tier, quality = classify_source("https://pib.gov.in/press-release")
    assert tier == "TIER_1"
    assert quality == "HIGH"


def test_tier_2_agency_domain() -> None:
    tier, quality = classify_source("https://nhai.org/project-update", agency_code="nhai")
    assert tier == "TIER_2"
    assert quality == "HIGH"


def test_tier_3_established_news() -> None:
    tier, quality = classify_source("https://www.thehindu.com/news/national/article")
    assert tier == "TIER_3"
    assert quality == "MEDIUM"


def test_tier_4_other_secondary_source() -> None:
    tier, quality = classify_source("https://randomblog.example.com/post")
    assert tier == "TIER_4"
    assert quality == "LOW"


def test_tier_5_unverifiable_source() -> None:
    tier, quality = classify_source("not-a-real-url")
    assert tier == "TIER_5"
    assert quality == "UNVERIFIED"
