from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rqg.cli import main
from rqg.quality.check import CheckResult, ThresholdResult, build_gate_decision
from rqg.quality.staleness import CaseStalenessItem


def assert_gate_report_bundle_contract(payload: dict) -> None:
    """Assert the stable gate-report.json contract while allowing additive fields."""
    assert {
        "decision",
        "history_summary",
        "report_markdown",
        "artifact_paths",
    }.issubset(payload)

    decision = payload["decision"]
    assert isinstance(decision, dict)
    assert {
        "run_id",
        "status",
        "reasons",
        "metrics",
        "next_actions",
        "created_at",
    }.issubset(decision)
    assert isinstance(decision["run_id"], str)
    assert decision["status"] in {"pass", "warn", "fail"}
    assert isinstance(decision["reasons"], list)
    assert isinstance(decision["metrics"], dict)
    assert isinstance(decision["next_actions"], list)
    assert isinstance(decision["created_at"], str)

    assert {
        "overall_pass_rate",
        "s1_pass_rate",
        "current_runs",
        "baseline_runs",
    }.issubset(decision["metrics"])
    for key in ("overall_pass_rate", "s1_pass_rate", "current_runs", "baseline_runs"):
        assert isinstance(decision["metrics"][key], (int, float))

    for action in decision["next_actions"]:
        assert isinstance(action, dict)
        assert {
            "failure_category",
            "count",
            "action",
            "owner",
            "due",
            "affected_case_ids",
        }.issubset(action)
        assert isinstance(action["failure_category"], str)
        assert isinstance(action["count"], int)
        assert isinstance(action["action"], str)
        assert isinstance(action["owner"], str)
        assert isinstance(action["due"], str)
        assert isinstance(action["affected_case_ids"], list)

    history_summary = payload["history_summary"]
    assert isinstance(history_summary, dict)
    assert {
        "entries",
        "status_mix",
        "week_start",
        "compare_offset",
        "trend_window",
        "summary_lines",
        "trend",
        "comparison",
        "failure_action_coverage",
        "uncovered_categories",
        "stale_case_review",
        "review_steward",
    }.issubset(history_summary)
    assert isinstance(history_summary["entries"], int)
    assert isinstance(history_summary["status_mix"], dict)
    assert {"pass", "warn", "fail"}.issubset(history_summary["status_mix"])
    for key in ("pass", "warn", "fail"):
        assert isinstance(history_summary["status_mix"][key], int)
    assert history_summary["week_start"] is None or isinstance(
        history_summary["week_start"], str
    )
    assert isinstance(history_summary["compare_offset"], int)
    assert isinstance(history_summary["trend_window"], int)
    assert isinstance(history_summary["summary_lines"], list)
    assert history_summary["trend"] is None or isinstance(history_summary["trend"], dict)
    assert history_summary["comparison"] is None or isinstance(
        history_summary["comparison"], dict
    )
    assert history_summary["failure_action_coverage"] is None or isinstance(
        history_summary["failure_action_coverage"], dict
    )
    assert isinstance(history_summary["uncovered_categories"], list)
    assert history_summary["stale_case_review"] is None or isinstance(
        history_summary["stale_case_review"], dict
    )
    assert history_summary["review_steward"] is None or isinstance(
        history_summary["review_steward"], str
    )

    assert isinstance(payload["report_markdown"], str)

    artifact_paths = payload["artifact_paths"]
    assert isinstance(artifact_paths, dict)
    assert {
        "report_path",
        "decision_path",
        "history_summary_path",
        "history_path",
        "bundle_path",
    }.issubset(artifact_paths)
    for key in (
        "report_path",
        "decision_path",
        "history_summary_path",
        "history_path",
        "bundle_path",
    ):
        assert isinstance(artifact_paths[key], str)


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
    assert (log_dir / "gate-report.json").exists()
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
    bundle_path = log_dir / "gate-report.json"
    decision_path = log_dir / "gate-decision.json"
    summary_path = log_dir / "gate-history-summary.json"
    assert report_path.exists()
    assert bundle_path.exists()
    assert decision_path.exists()
    assert summary_path.exists()
    history_path = log_dir / "gate-decisions.jsonl"
    assert history_path.exists()
    assert report_path.read_text(encoding="utf-8") == "md-default"
    bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    payload = decision_path.read_text(encoding="utf-8")
    assert '"run_id": "run-004"' in payload
    assert '"status": "fail"' in payload
    assert bundle_payload["decision"]["run_id"] == "run-004"
    assert bundle_payload["report_markdown"] == "md-default"
    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_payload["entries"] == 1
    assert summary_payload["trend"]["latest_run_id"] == "run-004"
    history_lines = [line for line in history_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(history_lines) == 1
    assert json.loads(history_lines[0])["run_id"] == "run-004"


def test_gate_report_json_bundle_schema_contract() -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-gate-report-contract"
    fake_result = CheckResult(
        run_id="run-contract",
        current_runs=5,
        baseline_runs=2,
        overall_rate=60.0,
        s1_rate=50.0,
        s1_passed=1,
        s1_total=2,
        thresholds=[
            ThresholdResult("Overall pass rate", 80.0, 60.0, False, "3/5"),
            ThresholdResult("S1 pass rate", 100.0, 50.0, False, "1/2"),
        ],
        failure_categories={"retrieval_miss": 2},
        failure_case_ids={"retrieval_miss": ["QA-1", "QA-2"]},
        avg_judge_relevance=70.0,
        judge_relevance_scored=5,
        avg_evidence_recall=80.0,
        evidence_recall_scored=5,
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch(
            "rqg.quality.check.render_gate_markdown",
            return_value="## RAG Quality Gate: FAIL\n",
        ):
            exit_code = main(["check", "--log-dir", str(log_dir)])

    assert exit_code == 1
    bundle_path = log_dir / "gate-report.json"
    assert bundle_path.exists()

    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert_gate_report_bundle_contract(payload)
    assert payload["decision"]["run_id"] == "run-contract"
    assert payload["decision"]["status"] == "fail"
    assert payload["decision"]["metrics"]["avg_judge_relevance"] == 70.0
    assert payload["decision"]["metrics"]["avg_evidence_recall"] == 80.0
    assert payload["decision"]["next_actions"][0]["failure_category"] == "retrieval_miss"
    assert payload["decision"]["next_actions"][0]["affected_case_ids"] == ["QA-1", "QA-2"]
    assert payload["history_summary"]["entries"] == 1
    assert payload["artifact_paths"]["bundle_path"].endswith("gate-report.json")


def test_check_command_overrides_aggregation_policy() -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-aggregation-logs"
    fake_result = CheckResult(
        run_id="run-agg",
        aggregation_policy="window",
        current_runs=4,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[
            ThresholdResult("Overall pass rate", 80.0, 100.0, True, "4/4"),
        ],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result) as mocked_run_check:
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-window"):
            exit_code = main(
                [
                    "check",
                    "--log-dir",
                    str(log_dir),
                    "--aggregation-policy",
                    "window",
                ]
            )

    assert exit_code == 0
    passed_config = mocked_run_check.call_args.kwargs["config"]
    assert passed_config.aggregation_policy == "window"


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


def test_check_command_gate_report_includes_recent_history_summary() -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-check-report-history"
    quality_pack = log_dir.parent / f"{uuid.uuid4()}-quality-pack.yml"
    quality_pack.write_text(
        """
common_failure_patterns:
  - name: retrieval_miss
    first_action: Review retrieval settings
""".strip(),
        encoding="utf-8",
    )
    first_result = CheckResult(
        run_id="run-201",
        current_runs=4,
        baseline_runs=0,
        overall_rate=75.0,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[
            ThresholdResult("Overall pass rate", 80.0, 75.0, False, "3/4"),
        ],
        failure_categories={"retrieval_miss": 1},
        failure_case_ids={"retrieval_miss": ["QA-1"]},
    )
    second_result = CheckResult(
        run_id="run-202",
        current_runs=5,
        baseline_runs=0,
        overall_rate=40.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[
            ThresholdResult("Overall pass rate", 80.0, 40.0, False, "2/5"),
            ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1"),
        ],
        failure_categories={"retrieval_miss": 2, "unknown": 1},
        failure_case_ids={"retrieval_miss": ["QA-2", "QA-3"], "unknown": ["QA-4"]},
    )

    with patch("rqg.quality.check.run_check", side_effect=[first_result, second_result]):
        first_exit = main(["check", "--log-dir", str(log_dir), "--quality-pack", str(quality_pack)])
        second_exit = main(
            ["check", "--log-dir", str(log_dir), "--quality-pack", str(quality_pack)]
        )

    assert first_exit == 1
    assert second_exit == 1
    report = (log_dir / "gate-report.md").read_text(encoding="utf-8")
    summary_payload = json.loads(
        (log_dir / "gate-history-summary.json").read_text(encoding="utf-8")
    )
    assert "### Recent History Summary" in report
    assert "Compared runs: run-201 -> run-202" in report
    assert "Failure action coverage (last 2): 1/2 categories (50.0%)" in report
    assert "Uncovered categories: unknown (1 case)" in report
    assert summary_payload["comparison"]["previous_run_id"] == "run-201"
    assert summary_payload["failure_action_coverage"]["coverage_rate"] == 50.0
    assert summary_payload["uncovered_categories"][0]["failure_category"] == "unknown"
    assert summary_payload["uncovered_categories"][0]["affected_case_ids"] == ["QA-4"]


def test_check_command_summary_includes_review_steward_and_stale_owner_rollup() -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-check-stale-owner-summary"
    quality_pack = log_dir.parent / f"{uuid.uuid4()}-quality-pack.yml"
    quality_pack.write_text(
        "\n".join(
            [
                "pack:",
                "  name: sample-pack",
                "  review_steward: ops-team",
                "common_failure_patterns:",
                "  - name: stale_case_definition",
                '    first_action: "Refresh stale case"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_result = CheckResult(
        run_id="run-stale-summary",
        current_runs=2,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[
            ThresholdResult("Overall pass rate", 80.0, 100.0, True, "2/2"),
        ],
        stale_after_days=30,
        fresh_case_review_rate=50.0,
        fresh_case_count=1,
        fresh_case_total=2,
        stale_cases=[
            CaseStalenessItem(
                case_id="QA-stale-1",
                name="stale",
                severity="S1",
                owner="hr-team",
                reference_field="last_reviewed_at",
                reference_value="2026-03-01",
                age_days=51,
                issue="older than 30 days",
            )
        ],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-stale"):
            exit_code = main(
                [
                    "check",
                    "--log-dir",
                    str(log_dir),
                    "--quality-pack",
                    str(quality_pack),
                ]
            )

    assert exit_code == 0
    summary_payload = json.loads(
        (log_dir / "gate-history-summary.json").read_text(encoding="utf-8")
    )
    assert summary_payload["review_steward"] == "ops-team"
    assert summary_payload["stale_case_review"]["stale_cases_count"] == 1
    assert summary_payload["stale_case_review"]["owners"][0]["owner"] == "hr-team"
    assert summary_payload["stale_case_review"]["owners"][0]["case_ids"] == ["QA-stale-1"]
