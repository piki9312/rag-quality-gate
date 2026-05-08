from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from rqg.cli import main
from rqg.serving.connection_validation import validate_http_rag_connection
from rqg.serving.external_adapter import (
    ExternalRAGAuthError,
    ExternalRAGServerError,
    ExternalRAGTimeoutError,
    HTTPRAGAdapter,
)

SENSITIVE_BODY = (
    "SECRET_TOKEN_ABC prompt text retrieved evidence "
    "/internal/customer/path.md sk-abcdefghijklmnopqrstuvwxyz1234567890"
)


def test_external_rag_500_body_is_redacted() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = SENSITIVE_BODY

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
        adapter = HTTPRAGAdapter(
            endpoint="https://rag.example.test/search?token=abcdefghijklmnopqrstuvwxyz1234567890"
        )
        with pytest.raises(ExternalRAGServerError) as excinfo:
            adapter.search("prompt text", top_k=1)

    message = str(excinfo.value)
    assert "External RAG API returned 500" in message
    assert "response body redacted" in message
    assert "SECRET_TOKEN_ABC" not in message
    assert "prompt text" not in message
    assert "retrieved evidence" not in message
    assert "/internal/customer/path.md" not in message
    assert "abcdefghijklmnopqrstuvwxyz1234567890" not in message

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
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


def test_validate_connection_stdout_redacts_endpoint_and_issue(capsys) -> None:
    raw_endpoint = "https://rag.example.test/search?" "api_key=abcdefghijklmnopqrstuvwxyz1234567890"
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = SENSITIVE_BODY

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
        exit_code = main(["validate-connection", "--endpoint", raw_endpoint])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Connection: NG" in captured.out
    assert raw_endpoint not in captured.out
    assert "abcdefghijklmnopqrstuvwxyz1234567890" not in captured.out
    assert "SECRET_TOKEN_ABC" not in captured.out
    assert "retrieved evidence" not in captured.out
    assert "/internal/customer/path.md" not in captured.out
    assert "response body redacted" in captured.out


def test_validate_connection_json_redacts_endpoint_and_issue(capsys) -> None:
    raw_endpoint = "https://rag.example.test/search?" "api_key=abcdefghijklmnopqrstuvwxyz1234567890"
    output = Path("tests/.tmp") / f"{uuid.uuid4()}-connection-validation.json"
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = SENSITIVE_BODY

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
        exit_code = main(
            [
                "validate-connection",
                "--endpoint",
                raw_endpoint,
                "--output",
                str(output),
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Saved validation JSON" in captured.out

    payload = json.loads(output.read_text(encoding="utf-8"))
    payload_text = json.dumps(payload, ensure_ascii=False)
    assert payload["ok"] is False
    assert payload["error_type"] == "server_error"
    assert raw_endpoint not in payload_text
    assert "abcdefghijklmnopqrstuvwxyz1234567890" not in payload_text
    assert "SECRET_TOKEN_ABC" not in payload_text
    assert "retrieved evidence" not in payload_text
    assert "/internal/customer/path.md" not in payload_text
    assert "response body redacted" in payload_text


def test_auth_error_body_is_redacted() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = SENSITIVE_BODY

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
        adapter = HTTPRAGAdapter(endpoint="https://rag.example.test/search")
        with pytest.raises(ExternalRAGAuthError) as excinfo:
            adapter.search("prompt text", top_k=1)

    message = str(excinfo.value)
    assert "External RAG API returned 401" in message
    assert "response body redacted" in message
    assert "SECRET_TOKEN_ABC" not in message
    assert "prompt text" not in message
    assert "retrieved evidence" not in message
    assert "/internal/customer/path.md" not in message


def test_external_rag_timeout_message_is_sanitized() -> None:
    adapter = HTTPRAGAdapter(endpoint="https://rag.example.com/search", timeout_sec=5.0)
    timeout = httpx.TimeoutException(
        "Request to https://rag.example.com/search failed with Bearer SECRET_TOKEN_ABC"
    )

    with patch("rqg.serving.external_adapter.httpx.post", side_effect=timeout):
        with pytest.raises(ExternalRAGTimeoutError) as excinfo:
            adapter.search("paid leave")

    message = str(excinfo.value)
    assert "timed out after 5.0s" in message
    assert "https://rag.example.com/search" not in message
    assert "SECRET_TOKEN_ABC" not in message
    assert "[REDACTED]" in message
