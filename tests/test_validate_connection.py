from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from rqg.cli import main


def test_validate_connection_success_writes_json(capsys) -> None:
    output = Path("tests/.tmp") / f"{uuid.uuid4()}-connection.json"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [{"chunk_id": "c1", "source": "policy.md", "text": "hello"}]
    }

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
        exit_code = main(
            [
                "validate-connection",
                "--endpoint",
                "https://rag.example.com/search",
                "--query",
                "paid leave",
                "--output",
                str(output),
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Connection: OK" in captured.out
    assert "https://rag.example.com/search" not in captured.out
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["endpoint"] == "[REDACTED]"
    assert payload["chunk_count"] == 1
    assert payload["endpoint"] == "[REDACTED]"
    assert payload["query"] == "[REDACTED]"
    assert payload["sample_sources"] == ["[REDACTED]"]


def test_validate_connection_returns_error_on_auth_failure(capsys) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized SECRET_TOKEN_ABC"

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
        exit_code = main(
            [
                "validate-connection",
                "--endpoint",
                "https://rag.example.com/search",
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Connection: NG" in captured.out
    assert "401" in captured.out
    assert "https://rag.example.com/search" not in captured.out
    assert "SECRET_TOKEN_ABC" not in captured.out
    assert "[REDACTED]" in captured.out


def test_validate_connection_reports_empty_result_diagnostics(capsys) -> None:
    output = Path("tests/.tmp") / f"{uuid.uuid4()}-connection-empty.json"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": []}

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
        exit_code = main(
            [
                "validate-connection",
                "--endpoint",
                "https://rag.example.com/search",
                "--query",
                "paid leave",
                "--output",
                str(output),
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Connection: OK" in captured.out
    assert "Chunks    : 0" in captured.out
    assert "empty contexts/sources" in captured.out

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["chunk_count"] == 0
    assert any("empty contexts/sources" in issue for issue in payload["issues"])
    assert payload["endpoint"] == "[REDACTED]"
    assert payload["query"] == "[REDACTED]"


def test_validate_connection_reports_schema_mismatch_diagnostics(capsys) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "answer": "Use the HR policy.",
        "data": [{"id": "c1", "body": "paid leave policy"}],
    }

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
        exit_code = main(
            [
                "validate-connection",
                "--endpoint",
                "https://rag.example.com/search",
                "--query",
                "paid leave",
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Connection: NG" in captured.out
    assert "missing 'results' or 'chunks' key" in captured.out
    assert "Available fields: answer, data" in captured.out
    assert "response_mapping" in captured.out
    assert "Use the HR policy." not in captured.out
    assert "paid leave policy" not in captured.out


def test_validate_connection_stdout_redacts_endpoint_and_issue(capsys) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "SECRET_TOKEN_ABC prompt text /internal/customer/path.md"

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
        exit_code = main(
            [
                "validate-connection",
                "--endpoint",
                "https://rag.example.com/search?token=SECRET_TOKEN_ABC",
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "https://rag.example.com/search" not in captured.out
    assert "SECRET_TOKEN_ABC" not in captured.out
    assert "/internal/customer/path.md" not in captured.out
    assert "response body redacted" in captured.out
    assert "Endpoint  : [REDACTED]" in captured.out


def test_validate_connection_json_redacts_endpoint_and_issue(capsys) -> None:
    output = Path("tests/.tmp") / f"{uuid.uuid4()}-connection-redacted.json"
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = (
        "Bearer SECRET_TOKEN_ABC https://rag.example.com/search "
        "/internal/customer/path.md expected_answer"
    )

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
        exit_code = main(
            [
                "validate-connection",
                "--endpoint",
                "https://rag.example.com/search?token=SECRET_TOKEN_ABC",
                "--output",
                str(output),
            ]
        )

    captured = capsys.readouterr()
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert payload["ok"] is False
    assert payload["endpoint"] == "[REDACTED]"
    assert payload["query"] == "[REDACTED]"
    assert payload["error_type"] == "auth_error"
    assert "403" in payload["issues"][0]
    assert "response body redacted" in payload["issues"][0]
    assert "SECRET_TOKEN_ABC" not in json.dumps(payload, ensure_ascii=False)
    assert "https://rag.example.com/search" not in json.dumps(payload, ensure_ascii=False)
    assert "/internal/customer/path.md" not in json.dumps(payload, ensure_ascii=False)
    assert "SECRET_TOKEN_ABC" not in captured.out
