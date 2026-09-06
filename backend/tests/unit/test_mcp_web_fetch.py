"""Unit tests for Web MCP's fetch_source safety logic (backend/app/mcp/web/
fetch.py) - all network/DNS calls mocked, hermetic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.mcp.web.fetch import safe_fetch


def test_rejects_non_http_scheme() -> None:
    result = safe_fetch("ftp://example.com/file")
    assert result.status == "REJECTED"
    assert result.rejected_reason == "UNSAFE_SCHEME"


def test_rejects_url_with_no_hostname() -> None:
    result = safe_fetch("http://")
    assert result.status == "REJECTED"
    assert result.rejected_reason == "UNSAFE_HOST"


def test_rejects_loopback_address() -> None:
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 0))]):
        result = safe_fetch("http://localhost/admin")
    assert result.status == "REJECTED"
    assert result.rejected_reason == "UNSAFE_HOST"


def test_rejects_private_range_address() -> None:
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("10.1.2.3", 0))]):
        result = safe_fetch("http://internal.example.com/")
    assert result.status == "REJECTED"
    assert result.rejected_reason == "UNSAFE_HOST"


def test_rejects_cloud_metadata_address() -> None:
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("169.254.169.254", 0))]):
        result = safe_fetch("http://metadata.internal/latest/meta-data")
    assert result.status == "REJECTED"
    assert result.rejected_reason == "UNSAFE_HOST"


def test_dns_resolution_failure_is_rejected() -> None:
    import socket

    with patch("socket.getaddrinfo", side_effect=socket.gaierror("no such host")):
        result = safe_fetch("http://does-not-resolve.example/")
    assert result.status == "REJECTED"
    assert result.rejected_reason == "DNS_RESOLUTION_FAILED"


def _public_addrinfo():
    return [(None, None, None, None, ("93.184.216.34", 0))]


def test_redirect_is_not_followed() -> None:
    mock_response = MagicMock()
    mock_response.is_redirect = True
    mock_response.status_code = 302
    mock_response.headers = {"location": "http://elsewhere.example/new", "content-type": "text/html"}
    mock_stream = MagicMock()
    mock_stream.__enter__.return_value = mock_response
    mock_stream.__exit__.return_value = False

    with (
        patch("socket.getaddrinfo", return_value=_public_addrinfo()),
        patch("httpx.stream", return_value=mock_stream) as mock_httpx_stream,
    ):
        result = safe_fetch("http://public.example.com/")

    assert result.status == "REDIRECT"
    assert result.redirect_location == "http://elsewhere.example/new"
    mock_httpx_stream.assert_called_once()
    kwargs = mock_httpx_stream.call_args.kwargs
    assert kwargs["follow_redirects"] is False


def test_response_is_truncated_at_max_bytes() -> None:
    mock_response = MagicMock()
    mock_response.is_redirect = False
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.encoding = "utf-8"
    mock_response.url = "http://public.example.com/"
    mock_response.iter_bytes.return_value = [b"x" * 100 for _ in range(10)]  # 1000 bytes total
    mock_stream = MagicMock()
    mock_stream.__enter__.return_value = mock_response
    mock_stream.__exit__.return_value = False

    with (
        patch("socket.getaddrinfo", return_value=_public_addrinfo()),
        patch("httpx.stream", return_value=mock_stream),
    ):
        result = safe_fetch("http://public.example.com/", max_bytes=250)

    assert result.status == "OK"
    assert result.truncated is True
    assert len(result.content_text) <= 250


def test_successful_fetch_returns_content() -> None:
    mock_response = MagicMock()
    mock_response.is_redirect = False
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.encoding = "utf-8"
    mock_response.url = "http://public.example.com/"
    mock_response.iter_bytes.return_value = [b"hello world"]
    mock_stream = MagicMock()
    mock_stream.__enter__.return_value = mock_response
    mock_stream.__exit__.return_value = False

    with (
        patch("socket.getaddrinfo", return_value=_public_addrinfo()),
        patch("httpx.stream", return_value=mock_stream),
    ):
        result = safe_fetch("http://public.example.com/")

    assert result.status == "OK"
    assert result.content_text == "hello world"
    assert result.truncated is False
