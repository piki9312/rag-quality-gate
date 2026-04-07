from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rqg.cli import main
from rqg.quality.check import CheckResult, ThresholdResult, build_gate_decision


def test_build_gate_decision_from_check_result_pass() -> None:
    result = CheckResult(
        run_id="run-001",
        current_runs=10,
        baseline_runs=5,
        overall_rate=90.0,
        s1_rate=100.0,
        s1_passed=3,
        s1_total=3,
        thresholds=[
            ThresholdResult("S1", 100.0, 100.0, True, "3/3"),
            ThresholdResult("Overall", 80.0, 90.0, True, "9/10"),
        ],
    )

    decision = build_gate_decision(result)

    assert decision.run_id == "run-001"
    assert decision.status == "pass"
    assert decision.metrics["overall_pass_rate"] == 90.0
    assert decision.reasons == []
    assert decision.next_actions == []


def test_build_gate_decision_from_check_result_fail() -> None:
    result = CheckResult(
        run_id="run-002",
        current_runs=10,
        baseline_runs=0,
        overall_rate=60.0,
        s1_rate=50.0,
        s1_passed=1,
        s1_total=2,
        thresholds=[
            ThresholdResult("S1 pass rate", 100.0, 50.0, False, "1/2"),
        ],
        case_thresholds=[
            ThresholdResult("case:QA001", 95.0, 80.0, False, "Critical case"),
        ],
        failure_categories={"retrieval_miss": 2, "unknown": 1},
    )

    decision = build_gate_decision(
        result,
        failure_actions={"retrieval_miss": "Review retrieval settings"},
    )

    assert decision.status == "fail"
    assert len(decision.reasons) == 2
    assert "case:QA001" in decision.reasons[1]
    actions = {item.failure_category: item for item in decision.next_actions}
    assert actions["retrieval_miss"].count == 2
    assert actions["retrieval_miss"].action == "Review retrieval settings"
    assert actions["unknown"].action == "Define next action in weekly review issue"


def test_check_command_writes_gate_decision_json() -> None:
    output = Path("tests/.tmp") / f"{uuid.uuid4()}-decision.json"
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-check-logs"
    fake_result = CheckResult(
        run_id="run-003",
        current_runs=3,
        baseline_runs=1,
        overall_rate=66.7,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[
            ThresholdResult("Overall pass rate", 80.0, 66.7, False, "2/3"),
        ],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md"):
            exit_code = main(
                [
                    "check",
                    "--log-dir",
                    str(log_dir),
                    "--decision-file",
                    str(output),
                ]
            )

    assert exit_code == 1
    assert output.exists()
    assert (log_dir / "gate-report.md").exists()
    assert (log_dir / "gate-decisions.jsonl").exists()
    payload = output.read_text(encoding="utf-8")
    assert '"run_id": "run-003"' in payload
    assert '"status": "fail"' in payload
    assert '"next_actions": []' in payload


def test_check_command_writes_default_artifacts_to_log_dir() -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-check-default-logs"
    fake_result = CheckResult(
        run_id="run-004",
        current_runs=4,
        baseline_runs=2,
        overall_rate=50.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[
            ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1"),
        ],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-default"):
            exit_code = main(["check", "--log-dir", str(log_dir)])

    assert exit_code == 1
    report_path = log_dir / "gate-report.md"
    decision_path = log_dir / "gate-decision.json"
    assert report_path.exists()
    assert decision_path.exists()
    history_path = log_dir / "gate-decisions.jsonl"
    assert history_path.exists()
    assert report_path.read_text(encoding="utf-8") == "md-default"
    payload = decision_path.read_text(encoding="utf-8")
    assert '"run_id": "run-004"' in payload
    assert '"status": "fail"' in payload
    history_lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(history_lines) == 1
    assert json.loads(history_lines[0])["run_id"] == "run-004"


def test_check_command_appends_gate_decision_history_jsonl() -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-check-history-logs"
    first_result = CheckResult(
        run_id="run-101",
        current_runs=4,
        baseline_runs=2,
        overall_rate=50.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[
            ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1"),
        ],
    )
    second_result = CheckResult(
        run_id="run-102",
        current_runs=5,
        baseline_runs=2,
        overall_rate=40.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[
            ThresholdResult("Overall pass rate", 80.0, 40.0, False, "2/5"),
        ],
    )

    with patch("rqg.quality.check.run_check", side_effect=[first_result, second_result]):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-history"):
            first_exit = main(["check", "--log-dir", str(log_dir)])
            second_exit = main(["check", "--log-dir", str(log_dir)])

    assert first_exit == 1
    assert second_exit == 1
    history_path = log_dir / "gate-decisions.jsonl"
    lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 2
    assert [json.loads(line)["run_id"] for line in lines] == ["run-101", "run-102"]
