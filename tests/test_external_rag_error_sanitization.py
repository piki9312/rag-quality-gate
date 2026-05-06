from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rqg.cli import main
from rqg.serving.external_adapter import (
    ExternalRAGAuthError,
    ExternalRAGServerError,
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
