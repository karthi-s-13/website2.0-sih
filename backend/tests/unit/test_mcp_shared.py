"""Unit tests for backend/app/mcp/_shared.py - the embedding-unavailable
fallback path, shared by Document MCP's search_documents and Knowledge
MCP's hybrid_search."""

from __future__ import annotations

from unittest.mock import patch

from app.core.errors import DataLeakageError, DataQualityFailureError, ModelUnavailableError, NotFoundError
from app.mcp._shared import error_envelope, resolve_query_embedding, run_hybrid_or_keyword_search, status_for_error


def test_resolve_query_embedding_returns_none_when_unavailable() -> None:
    from app.services.rag.embeddings import EmbeddingUnavailableError

    with patch("app.mcp._shared.embed_query", side_effect=EmbeddingUnavailableError("no key")):
        assert resolve_query_embedding("some query", api_key=None) is None


def test_resolve_query_embedding_returns_vector_on_success() -> None:
    with patch("app.mcp._shared.embed_query", return_value=[0.1, 0.2, 0.3]):
        assert resolve_query_embedding("some query", api_key="key") == [0.1, 0.2, 0.3]


def test_run_hybrid_or_keyword_search_falls_back_to_keyword_only() -> None:
    from app.services.rag.embeddings import EmbeddingUnavailableError

    with (
        patch("app.mcp._shared.embed_query", side_effect=EmbeddingUnavailableError("no key")),
        patch("app.mcp._shared.keyword_search", return_value=[]) as mock_keyword_search,
    ):
        ranked, embedding_used = run_hybrid_or_keyword_search(
            session=None, query_text="test query", top_k=5, api_key=None
        )

    assert embedding_used is False
    assert ranked == []
    mock_keyword_search.assert_called_once()


def test_run_hybrid_or_keyword_search_uses_hybrid_when_embedding_available() -> None:
    with (
        patch("app.mcp._shared.embed_query", return_value=[0.1, 0.2]),
        patch("app.mcp._shared.hybrid_search", return_value=["ranked-result"]) as mock_hybrid_search,
    ):
        ranked, embedding_used = run_hybrid_or_keyword_search(
            session=None, query_text="test query", top_k=5, api_key="key"
        )

    assert embedding_used is True
    assert ranked == ["ranked-result"]
    mock_hybrid_search.assert_called_once()


def test_status_for_error_maps_every_app_error_type() -> None:
    assert status_for_error(NotFoundError("x")) == "NOT_FOUND"
    assert status_for_error(DataQualityFailureError("x")) == "NOT_AVAILABLE"
    assert status_for_error(ModelUnavailableError("x")) == "NOT_AVAILABLE"
    assert status_for_error(DataLeakageError("x")) == "ERROR"


def test_error_envelope_never_downgrades_data_leakage() -> None:
    envelope = error_envelope(DataLeakageError("leak detected"))
    assert envelope["status"] == "ERROR"
    assert envelope["error_code"] == "DATA_LEAKAGE_DETECTED"
    assert envelope["message"] == "leak detected"
