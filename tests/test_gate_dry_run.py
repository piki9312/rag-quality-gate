from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from rqg.cli.check import cmd_check
from rqg.quality.check import CheckResult, ThresholdResult


def test_check_command_skips_history_append_and_notifications_when_disabled(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    fake_result = CheckResult(
        run_id="run-dry-check",
        current_runs=2,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[
            ThresholdResult("Overall pass rate", 80.0, 100.0, True, "2/2"),
        ],
    )

    args = SimpleNamespace(
        log_dir=str(log_dir),
        config=None,
        days=1,
        baseline_dir=None,
        baseline_days=7,
        cases_file=None,
        quality_pack=None,
        s1_threshold=100.0,
        overall_threshold=80.0,
        max_overall_drop_pct=None,
        max_s1_drop_pct=None,
        aggregation_policy=None,
        output_file=None,
        decision_file=None,
        bundle_file=None,
        warn_exit_code=0,
        append_history=False,
        notifications_enabled=False,
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="dry-md"):
            with patch("rqg.cli.check.send_gate_notifications") as notifications_mock:
                exit_code = cmd_check(args)

    assert exit_code == 0
    assert (log_dir / "gate-report.md").exists()
    assert (log_dir / "gate-report.json").exists()
    assert (log_dir / "gate-decision.json").exists()
    assert (log_dir / "gate-history-summary.json").exists()
    assert not (log_dir / "gate-decisions.jsonl").exists()
    assert not (log_dir / "gate-decisions-safe.jsonl").exists()
    notifications_mock.assert_not_called()
