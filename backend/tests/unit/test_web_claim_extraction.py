import json
from unittest.mock import patch

from app.services.web.claim_extraction import extract_claims
from app.services.web.search_client import SearchResult

RESULTS = [
    SearchResult(
        title="Bihar bridge project delayed by land acquisition dispute",
        url="https://www.thehindu.com/news/bihar-bridge-delay",
        content="The Test Bridge Project in Bihar has faced delays due to a land acquisition dispute.",
        published_date_raw="2025-08-14",
    ),
    SearchResult(
        title="Unrelated cricket news",
        url="https://example.com/cricket",
        content="India wins the match.",
        published_date_raw=None,
    ),
]


def test_extract_claims_no_api_key_uses_fallback() -> None:
    claims = extract_claims(
        api_key=None,
        model="gemini-3.6-flash",
        project_name="Test Bridge Project",
        agency="NHAI",
        state="Bihar",
        topic="land acquisition",
        results=RESULTS,
    )
    assert len(claims) == 2
    assert claims[0].project_relevance > claims[1].project_relevance
    assert claims[0].finding  # non-empty


def test_extract_claims_empty_results() -> None:
    claims = extract_claims(
        api_key="fake-key",
        model="gemini-3.6-flash",
        project_name="Test Bridge Project",
        agency="NHAI",
        state="Bihar",
        topic="land acquisition",
        results=[],
    )
    assert claims == []


def test_extract_claims_llm_failure_falls_back() -> None:
    with patch("app.services.llm.groq_client.generate_text", side_effect=RuntimeError("network down")):
        claims = extract_claims(
            api_key="fake-key",
            model="gemini-3.6-flash",
            project_name="Test Bridge Project",
            agency="NHAI",
            state="Bihar",
            topic="land acquisition",
            results=RESULTS,
        )
    assert len(claims) == 2


def test_extract_claims_success_uses_llm_output() -> None:
    llm_output = json.dumps(
        [
            {"finding": "Land acquisition dispute delayed the bridge project.", "project_relevance": 0.95},
            {"finding": "No specific project-relevant claim found in this source.", "project_relevance": 0.0},
        ]
    )

    with patch("app.services.llm.groq_client.generate_text", return_value=llm_output):
        claims = extract_claims(
            api_key="fake-key",
            model="gemini-3.6-flash",
            project_name="Test Bridge Project",
            agency="NHAI",
            state="Bihar",
            topic="land acquisition",
            results=RESULTS,
        )

    assert claims[0].finding == "Land acquisition dispute delayed the bridge project."
    assert claims[0].project_relevance == 0.95
    assert claims[1].project_relevance == 0.0


def test_extract_claims_malformed_llm_output_falls_back() -> None:
    with patch("app.services.llm.groq_client.generate_text", return_value="not valid json"):
        claims = extract_claims(
            api_key="fake-key",
            model="gemini-3.6-flash",
            project_name="Test Bridge Project",
            agency="NHAI",
            state="Bihar",
            topic="land acquisition",
            results=RESULTS,
        )
    assert len(claims) == 2  # fell back to deterministic extraction


def test_extract_claims_wrong_length_llm_output_falls_back() -> None:
    llm_output = json.dumps([{"finding": "only one", "project_relevance": 0.5}])

    with patch("app.services.llm.groq_client.generate_text", return_value=llm_output):
        claims = extract_claims(
            api_key="fake-key",
            model="gemini-3.6-flash",
            project_name="Test Bridge Project",
            agency="NHAI",
            state="Bihar",
            topic="land acquisition",
            results=RESULTS,
        )
    assert len(claims) == 2  # mismatched length -> fallback
