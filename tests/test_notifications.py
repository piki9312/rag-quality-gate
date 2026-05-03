from __future__ import annotations

import io
import json
import uuid
from pathlib import Path
from unittest.mock import patch

from rqg.cli import main
from rqg.quality.check import CheckResult, ThresholdResult


def test_check_sends_notifications_from_rqg_config() -> None:
    workspace = Path("tests/.tmp") / f"{uuid.uuid4()}-notify"
    workspace.mkdir(parents=True, exist_ok=True)
    log_dir = workspace / "logs"
    config_path = workspace / ".rqg.yml"
    decision_path = log_dir / "gate-decision.json"
    config_path.write_text(
        "\n".join(
            [
                "notifications:",
                "  - type: webhook",
                "    webhook_url: https://notify.example.test/hook",
                "    notify_on: [fail]",
                "thresholds:",
                "  s1_pass_rate: 100.0",
                "  overall_pass_rate: 80.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_result = CheckResult(
        run_id="run-notify",
        current_runs=2,
        baseline_runs=0,
        overall_rate=50.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-notify"):
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b"ok")) as mocked_urlopen:
                exit_code = main(["check", "--log-dir", str(log_dir), "--config", str(config_path)])

    assert exit_code == 1
    assert mocked_urlopen.called
    request = mocked_urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["event"] == "rqg.gate_decision"
    assert payload["status"] == "fail"
    assert payload["decision_path"] == str(decision_path)


def test_check_warns_when_notification_delivery_fails(capsys, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    workspace = Path("tests/.tmp") / f"{uuid.uuid4()}-notify-fail"
    workspace.mkdir(parents=True, exist_ok=True)
    log_dir = workspace / "logs"
    config_path = workspace / ".rqg.yml"
    config_path.write_text(
        "\n".join(
            [
                "notifications:",
                "  - type: slack",
                "    webhook_url: https://notify.example.test/slack",
                "    notify_on: [fail]",
                "thresholds:",
                "  s1_pass_rate: 100.0",
                "  overall_pass_rate: 80.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_result = CheckResult(
        run_id="run-notify-fail",
        current_runs=1,
        baseline_runs=0,
        overall_rate=0.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-notify"):
            with patch(
                "urllib.request.urlopen",
                side_effect=OSError("network down"),
            ):
                exit_code = main(["check", "--log-dir", str(log_dir), "--config", str(config_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Notification delivery failed" in captured.out
