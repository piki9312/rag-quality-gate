from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rqg.cli import main
from rqg.domain import GateDecision, GateNextAction
from rqg.quality.history import build_gate_history_summary_payload
from rqg.quality.staleness import CaseStalenessItem


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
    assert (
        "New reasons: S1 pass rate: 0.0 < 100.0 (0/1); Overall pass rate: 40.0 < 80.0 (4/10)"
        in captured.out
    )
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


def test_history_command_shows_reliability_signals(capsys) -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-history-reliability"
    log_dir.mkdir(parents=True, exist_ok=True)
    history_path = log_dir / "gate-decisions.jsonl"
    history_path.write_text(
        "\n".join(
            [
                '{"run_id":"run-1","status":"warn","reasons":[],"metrics":{"overall_pass_rate":100.0,"s1_pass_rate":100.0},"next_actions":[],"judge_fallback_used":true,"judge_fallback_count":1,"judge_failure_types":{"parse":1},"judge_reliability":"low","embedding_fallback_used":false,"embedding_fallback_count":0,"embedding_fallback_reason":null,"needs_human_review":true,"created_at":"2026-04-20T00:00:00Z"}',
                '{"run_id":"run-2","status":"pass","reasons":[],"metrics":{"overall_pass_rate":100.0,"s1_pass_rate":100.0},"next_actions":[],"judge_fallback_used":false,"judge_fallback_count":0,"judge_failure_types":{},"judge_reliability":"high","embedding_fallback_used":false,"embedding_fallback_count":0,"embedding_fallback_reason":null,"needs_human_review":false,"created_at":"2026-04-20T01:00:00Z"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(["history", "--log-dir", str(log_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Judge reliability: HIGH" in captured.out
    assert "Judge reliability change: LOW -> HIGH" in captured.out
    assert "Needs human review change: YES -> NO" in captured.out


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


def test_history_summary_uses_safe_projection_even_for_full_mode() -> None:
    raw_case_id = "ACME-SECRET-CASE"
    decision = GateDecision(
        run_id="run-history-safe",
        status="fail",
        policy_status="block",
        reasons=[
            "raw fail_reason question=How does ACME reset payroll? "
            "answer=Use raw answer expected_answer=golden answer "
            "source_doc=/customer/source/payroll.md"
        ],
        reason_codes=["retrieval_miss"],
        metrics={
            "overall_pass_rate": 25.0,
            "s1_pass_rate": 0.0,
            "s1_fail_count": 1.0,
            "current_runs": 4.0,
        },
        execution_mode="external_real",
        provenance={
            "prompt_hash": "prompt-hash-123",
            "index_version": "index-v7",
            "case_set_version": "cases-v2",
            "endpoint": "https://rag.example.test/search",
        },
        next_actions=[
            GateNextAction(
                failure_category="retrieval_miss",
                count=1,
                action="Define next action in weekly review issue",
                owner="customer-owner@example.test",
                affected_case_ids=[raw_case_id],
            )
        ],
        needs_human_review=True,
        judge_reliability="low",
        retrieval_reliability="medium",
        created_at=datetime.now(timezone.utc),
    )

    payload = build_gate_history_summary_payload(
        [decision],
        stale_cases=[
            CaseStalenessItem(
                case_id=raw_case_id,
                name="Customer-authored summary",
                severity="S1",
                owner="customer-owner@example.test",
                reference_field="source_doc",
                reference_value="/customer/source/payroll.md",
                age_days=42,
                issue="raw fail_reason includes customer text",
            )
        ],
        stale_after_days=30,
        fresh_case_review_rate=50.0,
        fresh_case_count=1,
        fresh_case_total=4,
        review_steward="customer-owner@example.test",
    )
    serialized = json.dumps(payload, ensure_ascii=False)

    for forbidden in [
        "How does ACME reset payroll?",
        "Use raw answer",
        "golden answer",
        "/customer/source/payroll.md",
        raw_case_id,
        "raw fail_reason",
        "Customer-authored summary",
        "customer-owner@example.test",
        "https://rag.example.test/search",
    ]:
        assert forbidden not in serialized

    assert payload["review_steward"] is None
    assert payload["uncovered_categories"][0]["case_id_hashes"]
    assert payload["stale_case_review"]["stale_cases"][0]["case_id_hash"]
    assert payload["comparison"] is None
    assert payload["reliability"]["judge_reliability"] == "low"
    assert payload["reliability"]["retrieval_reliability"] == "medium"
    assert payload["provenance"]["prompt_hash"] == "prompt-hash-123"
    assert payload["provenance"]["index_version"] == "index-v7"
    assert payload["provenance"]["case_set_version"] == "cases-v2"
    assert payload["stale_case_review"]["total_cases"] == 4
