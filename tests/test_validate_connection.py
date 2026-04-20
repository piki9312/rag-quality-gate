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
