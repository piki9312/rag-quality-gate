from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from rqg.serving.connection_validation import validate_http_rag_connection
from rqg.serving.external_adapter import (
    ExternalRAGAuthError,
    ExternalRAGServerError,
    ExternalRAGTimeoutError,
    HTTPRAGAdapter,
)


def test_external_rag_500_body_is_redacted() -> None:
    secret_body = (
        "SECRET_TOKEN_ABC prompt=employee salary answer "
        "retrieved evidence /internal/customer/path.md"
    )
    response = MagicMock()
    response.status_code = 500
    response.text = secret_body

    adapter = HTTPRAGAdapter(endpoint="https://rag.example.com/search")

    with patch("rqg.serving.external_adapter.httpx.post", return_value=response):
        try:
            adapter.search("paid leave")
        except ExternalRAGServerError as exc:
            message = str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected ExternalRAGServerError")

    assert "500" in message
    assert "response body redacted" in message
    assert "SECRET_TOKEN_ABC" not in message
    assert "employee salary" not in message
    assert "/internal/customer/path.md" not in message

    with patch("rqg.serving.external_adapter.httpx.post", return_value=response):
        result = validate_http_rag_connection(
            endpoint="https://rag.example.com/search",
            query="employee salary",
        )

    assert result.ok is False
    assert result.error_type == "server_error"
    assert any("response body redacted" in issue for issue in result.issues)
    combined = " ".join(result.issues)
    assert "SECRET_TOKEN_ABC" not in combined
    assert "employee salary" not in combined
    assert "/internal/customer/path.md" not in combined


def test_external_rag_auth_error_body_is_redacted() -> None:
    response = MagicMock()
    response.status_code = 401
    response.text = "Bearer SECRET_TOKEN_ABC prompt expected_answer"

    adapter = HTTPRAGAdapter(endpoint="https://rag.example.com/search")

    with patch("rqg.serving.external_adapter.httpx.post", return_value=response):
        try:
            adapter.search("paid leave")
        except ExternalRAGAuthError as exc:
            message = str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected ExternalRAGAuthError")

    assert "401" in message
    assert "response body redacted" in message
    assert "SECRET_TOKEN_ABC" not in message
    assert "expected_answer" not in message


def test_external_rag_timeout_message_is_sanitized() -> None:
    adapter = HTTPRAGAdapter(endpoint="https://rag.example.com/search", timeout_sec=5.0)
    timeout = httpx.TimeoutException(
        "Request to https://rag.example.com/search failed with Bearer SECRET_TOKEN_ABC"
    )

    with patch("rqg.serving.external_adapter.httpx.post", side_effect=timeout):
        try:
            adapter.search("paid leave")
        except ExternalRAGTimeoutError as exc:
            message = str(exc)
        else:  # pragma: no cover
            raise AssertionError("expected ExternalRAGTimeoutError")

    assert "timed out after 5.0s" in message
    assert "https://rag.example.com/search" not in message
    assert "SECRET_TOKEN_ABC" not in message
    assert "[REDACTED]" in message
