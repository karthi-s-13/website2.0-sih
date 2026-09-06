from unittest.mock import MagicMock, patch

from app.services.rag.answer import compose_answer
from app.services.rag.retrieval import RankedChunk


def make_ranked(document_name, page, text, score=0.5):
    document = MagicMock()
    document.document_name = document_name
    chunk = MagicMock()
    chunk.document = document
    chunk.page = page
    chunk.text = text
    return RankedChunk(chunk=chunk, score=score, matched_vector=True, matched_keyword=True)


RANKED = [make_ranked("ReviewReportOct25.pdf", 6, "Power sector achieved 97% of target in October 2025.")]


def test_no_api_key_uses_deterministic_fallback_with_citations() -> None:
    result = compose_answer(
        api_key=None,
        model="gemini-3.6-flash",
        question="What happened?",
        project_name="Test Project",
        ranked_chunks=RANKED,
    )
    assert result.source == "DETERMINISTIC_FALLBACK"
    assert "ReviewReportOct25.pdf" in result.text
    assert "p.6" in result.text
    assert len(result.citations) == 1
    assert result.citations[0].page == 6


def test_no_ranked_chunks_reports_no_evidence() -> None:
    result = compose_answer(
        api_key=None, model="gemini-3.6-flash", question="What happened?", project_name="Test Project", ranked_chunks=[]
    )
    assert result.source == "DETERMINISTIC_FALLBACK"
    assert "No retrieved evidence" in result.text
    assert result.citations == []


def test_llm_failure_falls_back() -> None:
    with patch("google.genai.Client", side_effect=RuntimeError("network down")):
        result = compose_answer(
            api_key="fake", model="gemini-3.6-flash", question="q", project_name="p", ranked_chunks=RANKED
        )
    assert result.source == "DETERMINISTIC_FALLBACK"


def test_llm_success_with_citation_is_used() -> None:
    fake_response = MagicMock()
    fake_response.text = "Power sector performance is discussed (ReviewReportOct25.pdf, p.6)."
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client):
        result = compose_answer(
            api_key="fake", model="gemini-3.6-flash", question="q", project_name="p", ranked_chunks=RANKED
        )
    assert result.source == "LLM"
    assert result.model == "gemini-3.6-flash"


def test_llm_output_without_any_citation_falls_back() -> None:
    """Guardrail: an answer that cites nothing from the retrieved evidence is
    rejected, even if the call itself succeeded."""
    fake_response = MagicMock()
    fake_response.text = "This project will definitely succeed with no issues at all."
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client):
        result = compose_answer(
            api_key="fake", model="gemini-3.6-flash", question="q", project_name="p", ranked_chunks=RANKED
        )
    assert result.source == "DETERMINISTIC_FALLBACK"


def test_llm_output_saying_no_relevant_evidence_is_accepted() -> None:
    fake_response = MagicMock()
    fake_response.text = "None of the provided excerpts mention this project; no relevant evidence was found."
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client):
        result = compose_answer(
            api_key="fake", model="gemini-3.6-flash", question="q", project_name="p", ranked_chunks=RANKED
        )
    assert result.source == "LLM"
