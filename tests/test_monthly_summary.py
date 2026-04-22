from __future__ import annotations

import json
import uuid
from pathlib import Path

from rqg.cli import main
from rqg.quality.monthly_summary import build_monthly_summary_payload


def test_build_monthly_summary_payload_counts_reliability_and_actions() -> None:
    decisions = [
        {
            "run_id": "run-1",
            "status": "warn",
            "reasons": ["WARN Overall pass rate: 85.0 < warn threshold 90.0"],
            "metrics": {
                "overall_pass_rate": 85.0,
                "s1_pass_rate": 100.0,
                "s1_fail_count": 0.0,
            },
            "next_actions": [],
            "judge_fallback_used": True,
            "judge_fallback_count": 1,
            "judge_failure_types": {"parse": 1},
            "judge_reliability": "low",
            "embedding_fallback_used": False,
            "embedding_fallback_count": 0,
            "embedding_fallback_reason": None,
            "needs_human_review": True,
            "created_at": "2026-04-02T00:00:00Z",
        },
        {
            "run_id": "run-2",
            "status": "fail",
            "reasons": ["S1 pass rate: 0.0 < 100.0 (0/1)"],
            "metrics": {
                "overall_pass_rate": 40.0,
                "s1_pass_rate": 0.0,
                "s1_fail_count": 1.0,
            },
            "next_actions": [
                {
                    "failure_category": "judge_reliability",
                    "count": 1,
                    "action": "Re-run judge-enabled evaluation and confirm model/API connectivity",
                    "owner": "T.B.D.",
                    "due": "T.B.D.",
                    "affected_case_ids": [],
                }
            ],
            "judge_fallback_used": False,
            "judge_fallback_count": 0,
            "judge_failure_types": {},
            "judge_reliability": "high",
            "embedding_fallback_used": True,
            "embedding_fallback_count": 1,
            "embedding_fallback_reason": "dependency_missing",
            "needs_human_review": True,
            "created_at": "2026-04-03T00:00:00Z",
        },
    ]
    gate_decisions_path = Path("tests/.tmp") / f"{uuid.uuid4()}-monthly-decisions.jsonl"
    gate_decisions_path.parent.mkdir(parents=True, exist_ok=True)
    gate_decisions_path.write_text(
        "\n".join(json.dumps(item) for item in decisions) + "\n",
        encoding="utf-8",
    )

    from rqg.quality.history import load_gate_decision_history

    payload = build_monthly_summary_payload(
        load_gate_decision_history(gate_decisions_path),
        month="2026-04",
    )

    assert payload["total_runs"] == 2
    assert payload["blocked_runs"] == 1
    assert payload["s1_incidents_detected"] == 1
    assert payload["fallback_trend"]["judge_fallback_runs"] == 1
    assert payload["fallback_trend"]["embedding_fallback_runs"] == 1
    assert payload["recommended_actions"][0]["failure_category"] == "judge_reliability"


def test_monthly_summary_command_writes_markdown_and_json(tmp_path, capsys) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    history_path = log_dir / "gate-decisions.jsonl"
    history_path.write_text(
        "\n".join(
            [
                '{"run_id":"run-1","status":"pass","reasons":[],"metrics":{"overall_pass_rate":100.0,"s1_pass_rate":100.0,"s1_fail_count":0.0},"next_actions":[],"judge_fallback_used":false,"judge_fallback_count":0,"judge_failure_types":{},"judge_reliability":"high","embedding_fallback_used":false,"embedding_fallback_count":0,"embedding_fallback_reason":null,"needs_human_review":false,"created_at":"2026-04-01T00:00:00Z"}',
                '{"run_id":"run-2","status":"fail","reasons":["Overall pass rate: 40.0 < 80.0 (2/5)"],"metrics":{"overall_pass_rate":40.0,"s1_pass_rate":100.0,"s1_fail_count":0.0},"next_actions":[],"judge_fallback_used":true,"judge_fallback_count":1,"judge_failure_types":{"parse":1},"judge_reliability":"low","embedding_fallback_used":false,"embedding_fallback_count":0,"embedding_fallback_reason":null,"needs_human_review":true,"created_at":"2026-04-02T00:00:00Z"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(["monthly-summary", "--log-dir", str(log_dir), "--month", "2026-04"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Monthly Quality Summary" in captured.out
    assert (log_dir / "monthly-summary.json").exists()
    assert (log_dir / "monthly-summary.md").exists()
