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
    records = [
        {
            "run_id": "run-1",
            "status": "pass",
            "reasons": [],
            "metrics": {
                "overall_pass_rate": 100.0,
                "s1_pass_rate": 100.0,
                "s1_fail_count": 0.0,
            },
            "next_actions": [],
            "judge_fallback_used": False,
            "judge_fallback_count": 0,
            "judge_failure_types": {},
            "judge_reliability": "high",
            "embedding_fallback_used": False,
            "embedding_fallback_count": 0,
            "embedding_fallback_reason": None,
            "needs_human_review": False,
            "created_at": "2026-04-01T00:00:00Z",
        },
        {
            "run_id": "run-2",
            "status": "fail",
            "reasons": ["Overall pass rate: 40.0 < 80.0 (2/5)"],
            "metrics": {
                "overall_pass_rate": 40.0,
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
    ]
    history_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )

    exit_code = main(["monthly-summary", "--log-dir", str(log_dir), "--month", "2026-04"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Monthly Quality Summary" in captured.out
    assert (log_dir / "monthly-summary.json").exists()
    assert (log_dir / "monthly-summary.md").exists()


def test_monthly_summary_prefers_safe_gate_decision_history(tmp_path, capsys) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "gate-decisions.jsonl").write_text(
        json.dumps(
            {
                "run_id": "raw-run",
                "question": "How does ACME reset payroll?",
                "answer": "Use raw answer",
                "expected_answer": "golden answer",
                "source_doc": "/customer/source/payroll.md",
                "case_id": "ACME-SECRET-CASE",
                "fail_reason": "raw fail_reason",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (log_dir / "gate-decisions-safe.jsonl").write_text(
        json.dumps(_safe_history_record(run_id="safe-run")) + "\n",
        encoding="utf-8",
    )

    exit_code = main(["monthly-summary", "--log-dir", str(log_dir), "--month", "2026-04"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Monthly Quality Summary" in captured.out
    payload = json.loads((log_dir / "monthly-summary.json").read_text(encoding="utf-8"))
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "How does ACME reset payroll?" not in serialized
    assert "Use raw answer" not in serialized
    assert "golden answer" not in serialized
    assert "/customer/source/payroll.md" not in serialized
    assert "ACME-SECRET-CASE" not in serialized
    assert "raw fail_reason" not in serialized
    assert "abc123def4567890" in serialized
    assert "retrieval_fail" in serialized
    assert payload["total_runs"] == 1
    assert payload["blocked_runs"] == 1
    assert payload["s1_incidents_detected"] == 1


def test_monthly_summary_falls_back_to_raw_gate_decision_history(tmp_path, capsys) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "gate-decisions.jsonl").write_text(
        json.dumps(_raw_history_record(run_id="raw-run")) + "\n",
        encoding="utf-8",
    )

    exit_code = main(["monthly-summary", "--log-dir", str(log_dir), "--month", "2026-04"])

    assert exit_code == 0
    capsys.readouterr()
    payload = json.loads((log_dir / "monthly-summary.json").read_text(encoding="utf-8"))
    assert payload["total_runs"] == 1
    assert payload["top_reasons"][0]["reason"] == "fallback_raw_reason"


def _safe_history_record(*, run_id: str) -> dict[str, object]:
    return {
        "run_id": run_id,
        "created_at": "2026-04-02T00:00:00Z",
        "gate_status": "fail",
        "policy_status": "block",
        "report_mode": "full",
        "execution_mode": "external_real",
        "overall_pass_rate": 25.0,
        "s1_pass_rate": 0.0,
        "total_cases": 4.0,
        "failed_cases": 1.0,
        "s1_failed_count": 1.0,
        "needs_human_review": True,
        "judge_reliability": "low",
        "retrieval_reliability": "medium",
        "safe_reason_codes": ["retrieval_fail"],
        "reason_codes": ["retrieval_fail"],
        "failure_type_code": "retrieval_fail",
        "failure_category": "retrieval_fail",
        "case_id_hash": "abc123def4567890",
        "case_id_hashes": ["abc123def4567890"],
        "aggregate_counts": {
            "judge_fallback_count": 1,
            "embedding_fallback_count": 0,
            "baseline_runs": 2.0,
            "current_runs": 4.0,
        },
        "prompt_hash": "prompt-hash-123",
        "index_version": "index-v7",
        "case_set_version": "cases-v2",
        "quality_pack_version": "pack-v3",
    }


def _raw_history_record(*, run_id: str) -> dict[str, object]:
    return {
        "run_id": run_id,
        "status": "warn",
        "reasons": ["fallback_raw_reason"],
        "metrics": {
            "overall_pass_rate": 90.0,
            "s1_pass_rate": 100.0,
            "s1_fail_count": 0.0,
        },
        "next_actions": [],
        "created_at": "2026-04-03T00:00:00Z",
    }
