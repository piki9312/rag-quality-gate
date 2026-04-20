from __future__ import annotations

import uuid
from pathlib import Path

from rqg.cli import main


def test_history_command_renders_recent_gate_decisions(capsys) -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-history-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    history_path = log_dir / "gate-decisions.jsonl"
    history_path.write_text(
        "\n".join(
            [
                '{"run_id":"run-1","status":"pass","reasons":[],"metrics":{"overall_pass_rate":100.0},"next_actions":[],"created_at":"2026-04-20T00:00:00Z"}',
                '{"run_id":"run-2","status":"fail","reasons":["S1 pass rate: 50.0 < 100.0"],"metrics":{"overall_pass_rate":50.0},"next_actions":[],"created_at":"2026-04-20T01:00:00Z"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(["history", "--log-dir", str(log_dir), "--last", "1"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Gate Decision History" in captured.out
    assert "run-2" in captured.out
    assert "run-1" not in captured.out


def test_history_command_returns_error_when_missing(capsys) -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-history-empty"

    exit_code = main(["history", "--log-dir", str(log_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No gate decision history found" in captured.out
