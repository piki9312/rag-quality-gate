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
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["chunk_count"] == 1
    assert payload["sample_sources"] == ["policy.md"]


def test_validate_connection_returns_error_on_auth_failure(capsys) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

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
