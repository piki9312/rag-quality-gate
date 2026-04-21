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
    assert "Latest Change Summary" not in captured.out


def test_history_command_renders_trend_and_latest_diff_summary(capsys) -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-history-diff"
    log_dir.mkdir(parents=True, exist_ok=True)
    history_path = log_dir / "gate-decisions.jsonl"
    history_path.write_text(
        "\n".join(
            [
                '{"run_id":"run-1","status":"pass","reasons":[],"metrics":{"overall_pass_rate":100.0,"s1_pass_rate":100.0,"current_runs":10.0},"next_actions":[],"created_at":"2026-04-20T00:00:00Z"}',
                '{"run_id":"run-2","status":"warn","reasons":["WARN Overall pass rate: 78.0 < warn threshold 85.0"],"metrics":{"overall_pass_rate":78.0,"s1_pass_rate":100.0,"current_runs":10.0},"next_actions":[{"failure_category":"retrieval_miss","count":1,"action":"Review retrieval settings","owner":"T.B.D.","due":"T.B.D.","affected_case_ids":["QA-1"]}],"created_at":"2026-04-20T01:00:00Z"}',
                '{"run_id":"run-3","status":"fail","reasons":["S1 pass rate: 0.0 < 100.0 (0/1)","Overall pass rate: 40.0 < 80.0 (4/10)"],"metrics":{"overall_pass_rate":40.0,"s1_pass_rate":0.0,"current_runs":10.0},"next_actions":[{"failure_category":"retrieval_miss","count":3,"action":"Review retrieval settings","owner":"T.B.D.","due":"T.B.D.","affected_case_ids":["QA-1","QA-2","QA-3"]},{"failure_category":"stale","count":1,"action":"Refresh document snapshot","owner":"T.B.D.","due":"T.B.D.","affected_case_ids":["QA-9"]},{"failure_category":"unknown","count":2,"action":"Define next action in weekly review issue","owner":"T.B.D.","due":"T.B.D.","affected_case_ids":["QA-7","QA-8"]}],"created_at":"2026-04-20T02:00:00Z"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(["history", "--log-dir", str(log_dir), "--last", "3"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Recent sequence (oldest -> latest, last 3): PASS -> WARN -> FAIL" in captured.out
    assert "Latest Change Summary" in captured.out
    assert "Compared runs: run-2 -> run-3" in captured.out
    assert "Status change: WARN -> FAIL" in captured.out
    assert "Overall pass rate: 78.0% -> 40.0% (-38.0 pts)" in captured.out
    assert "S1 pass rate: 100.0% -> 0.0% (-100.0 pts)" in captured.out
    assert "New reasons: S1 pass rate: 0.0 < 100.0 (0/1); Overall pass rate: 40.0 < 80.0 (4/10)" in captured.out
    assert "Resolved reasons: WARN Overall pass rate: 78.0 < warn threshold 85.0" in captured.out
    assert "Failure action coverage (last 3): 2/3 categories (66.7%)" in captured.out
    assert "Uncovered categories: unknown (2 cases)" in captured.out
    assert "retrieval_miss: 1 -> 3 (+2)" in captured.out
    assert "stale: 0 -> 1 (+1)" in captured.out


def test_history_command_surfaces_recent_action_coverage_gaps(capsys) -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-history-coverage"
    log_dir.mkdir(parents=True, exist_ok=True)
    history_path = log_dir / "gate-decisions.jsonl"
    history_path.write_text(
        "\n".join(
            [
                '{"run_id":"run-1","status":"fail","reasons":["Overall pass rate: 60.0 < 80.0 (6/10)"],"metrics":{"overall_pass_rate":60.0},"next_actions":[{"failure_category":"retrieval_miss","count":2,"action":"Review retrieval settings","owner":"T.B.D.","due":"T.B.D.","affected_case_ids":["QA-1","QA-2"]}],"created_at":"2026-04-20T00:00:00Z"}',
                '{"run_id":"run-2","status":"fail","reasons":["Overall pass rate: 50.0 < 80.0 (5/10)"],"metrics":{"overall_pass_rate":50.0},"next_actions":[{"failure_category":"unknown","count":3,"action":"Define next action in weekly review issue","owner":"T.B.D.","due":"T.B.D.","affected_case_ids":["QA-5","QA-6","QA-7"]}],"created_at":"2026-04-20T01:00:00Z"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(["history", "--log-dir", str(log_dir), "--last", "2"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Failure action coverage (last 2): 1/2 categories (50.0%)" in captured.out
    assert "Uncovered categories: unknown (3 cases)" in captured.out


def test_history_command_compare_offset_skips_to_older_baseline(capsys) -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-history-offset"
    log_dir.mkdir(parents=True, exist_ok=True)
    history_path = log_dir / "gate-decisions.jsonl"
    history_path.write_text(
        "\n".join(
            [
                '{"run_id":"run-1","status":"pass","reasons":[],"metrics":{"overall_pass_rate":100.0,"s1_pass_rate":100.0},"next_actions":[],"created_at":"2026-04-20T00:00:00Z"}',
                '{"run_id":"run-2","status":"warn","reasons":["WARN Overall pass rate: 85.0 < warn threshold 90.0"],"metrics":{"overall_pass_rate":85.0,"s1_pass_rate":100.0},"next_actions":[],"created_at":"2026-04-20T01:00:00Z"}',
                '{"run_id":"run-3","status":"fail","reasons":["Overall pass rate: 50.0 < 80.0 (5/10)"],"metrics":{"overall_pass_rate":50.0,"s1_pass_rate":50.0},"next_actions":[],"created_at":"2026-04-20T02:00:00Z"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "history",
            "--log-dir",
            str(log_dir),
            "--compare-offset",
            "2",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Compared runs: run-1 -> run-3" in captured.out
    assert "Status change: PASS -> FAIL" in captured.out


def test_history_command_returns_error_when_missing(capsys) -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-history-empty"

    exit_code = main(["history", "--log-dir", str(log_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No gate decision history found" in captured.out


def test_history_command_rejects_invalid_compare_offset(capsys) -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-history-invalid"

    exit_code = main(["history", "--log-dir", str(log_dir), "--compare-offset", "0"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "--compare-offset must be >= 1" in captured.out
