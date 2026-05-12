from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rqg.cli import main
from rqg.quality.check import CheckResult, ThresholdResult, build_gate_decision
from rqg.quality.models import QARunRecord, QATestCase
from rqg.quality.reporting import (
    GateReportArtifacts,
    build_ci_safe_history_summary_payload,
    build_gate_report_bundle_payload,
)
from rqg.quality.staleness import CaseStalenessItem


def assert_gate_report_bundle_contract(payload: dict) -> None:
    """Assert the stable gate-report.json contract while allowing additive fields."""
    assert {
        "schema_version",
        "decision",
        "history_summary",
        "report_markdown",
        "artifact_paths",
    }.issubset(payload)
    assert payload["schema_version"] == "1.0"

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
    assert history_summary["week_start"] is None or isinstance(history_summary["week_start"], str)
    assert isinstance(history_summary["compare_offset"], int)
    assert isinstance(history_summary["trend_window"], int)
    assert isinstance(history_summary["summary_lines"], list)
    assert history_summary["trend"] is None or isinstance(history_summary["trend"], dict)
    assert history_summary["comparison"] is None or isinstance(history_summary["comparison"], dict)
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


def assert_no_absolute_artifact_paths(payload: dict) -> None:
    artifact_paths = payload["artifact_paths"]
    for value in artifact_paths.values():
        assert not Path(value).is_absolute()
        assert ":\\" not in value
        assert "\\" not in value
        assert ".tmp" not in value


def _minimal_history_summary() -> dict[str, object]:
    return {
        "entries": 1,
        "status_mix": {"pass": 0, "warn": 0, "fail": 1},
        "week_start": None,
        "compare_offset": 1,
        "trend_window": 5,
        "summary_lines": [],
        "trend": {"latest_run_id": "run-case-projection"},
        "comparison": None,
        "failure_action_coverage": None,
        "uncovered_categories": [],
        "stale_case_review": None,
        "review_steward": None,
    }


def _make_bundle_artifacts(
    result: CheckResult,
    *,
    pack_metadata: dict[str, object] | None = None,
) -> GateReportArtifacts:
    decision = build_gate_decision(result, pack_metadata=pack_metadata)
    return GateReportArtifacts(
        markdown="md",
        decision=decision,
        history_summary=_minimal_history_summary(),
        report_path=Path("gate-report.md"),
        decision_path=Path("gate-decision.json"),
        history_summary_path=Path("gate-history-summary.json"),
        history_path=Path("gate-decisions.jsonl"),
        bundle_path=Path("gate-report.json"),
        check_result=result,
    )


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
    assert payload["artifact_paths"]["bundle_path"] == "gate-report.json"
    assert_no_absolute_artifact_paths(payload)


def test_gate_report_json_artifact_paths_are_relative_to_bundle() -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-gate-report-relative"
    fake_result = CheckResult(
        run_id="run-relative",
        current_runs=1,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[ThresholdResult("Overall pass rate", 80.0, 100.0, True, "1/1")],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-relative"):
            exit_code = main(
                [
                    "check",
                    "--log-dir",
                    str(log_dir),
                    "--output-file",
                    str(log_dir / "nested" / "gate-report.md"),
                    "--decision-file",
                    str(log_dir / "nested" / "gate-decision.json"),
                    "--bundle-file",
                    str(log_dir / "nested" / "gate-report.json"),
                ]
            )

    assert exit_code == 0
    payload = json.loads((log_dir / "nested" / "gate-report.json").read_text(encoding="utf-8"))
    assert_gate_report_bundle_contract(payload)
    assert_no_absolute_artifact_paths(payload)
    assert payload["artifact_paths"]["report_path"] == "gate-report.md"
    assert payload["artifact_paths"]["decision_path"] == "gate-decision.json"
    assert payload["artifact_paths"]["history_summary_path"] == "../gate-history-summary.json"
    assert payload["artifact_paths"]["history_path"] == "../gate-decisions.jsonl"
    assert payload["artifact_paths"]["bundle_path"] == "gate-report.json"


def test_gate_report_json_does_not_expose_tmp_artifact_paths() -> None:
    result = CheckResult(
        run_id="run-tmp-path",
        current_runs=1,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[ThresholdResult("Overall pass rate", 80.0, 100.0, True, "1/1")],
    )
    artifacts = _make_bundle_artifacts(result)
    artifacts = GateReportArtifacts(
        markdown=artifacts.markdown,
        decision=artifacts.decision,
        history_summary=artifacts.history_summary,
        report_path=Path("demos/customer/reports/gate-report.md"),
        decision_path=Path(".tmp/demo/gate-decision.json"),
        history_summary_path=Path(".tmp/demo/gate-history-summary.json"),
        history_path=Path(".tmp/demo/gate-decisions.jsonl"),
        bundle_path=Path("demos/customer/reports/gate-report.json"),
        check_result=result,
    )

    payload = build_gate_report_bundle_payload(artifacts)

    assert_no_absolute_artifact_paths(payload)
    assert payload["artifact_paths"]["decision_path"] == "gate-decision.json"
    assert payload["artifact_paths"]["history_summary_path"] == "gate-history-summary.json"
    assert payload["artifact_paths"]["history_path"] == "gate-decisions.jsonl"


def test_build_gate_report_bundle_payload_adds_customer_fields_preserving_contract() -> None:
    result = CheckResult(
        run_id="run-case-projection",
        current_runs=1,
        baseline_runs=0,
        overall_rate=0.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
        judge_fallback_count=1,
        judge_reliability="low",
        current_records=[
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="run-case-projection",
                case_id="QA001",
                severity="S1",
                category="policy",
                risk_domain="refund",
                required_action="block",
                passed=False,
                failure_type="judge_fallback",
                failure_category="judge_reliability",
                reasons=["Judge returned invalid payload"],
                answer="返金できます",
                retrieved_ids=["refund_policy"],
                judge_fallback_used=True,
                judge_fallback_reason="parse_error",
            )
        ],
        active_cases=[
            QATestCase(
                case_id="QA001",
                name="Refund answer",
                question="返金できますか",
                severity="S1",
                expected_answer="返金条件を案内する",
                expected_evidence=["refund_policy"],
                category="policy",
                risk_domain="refund",
                source_doc="refund.md",
            )
        ],
    )

    payload = build_gate_report_bundle_payload(
        _make_bundle_artifacts(
            result,
            pack_metadata={
                "tenant_name": "acme",
                "pack_name": "Support FAQ",
                "change_event": None,
            },
        )
    )

    assert_gate_report_bundle_contract(payload)
    assert payload["report_version"] == "1.0"
    assert payload["client_name"] == "acme"
    assert payload["app_name"] == "Support FAQ"
    assert payload["executed_at"] == payload["decision"]["created_at"]
    assert payload["target_docs"] == ["refund.md"]
    assert payload["change_event"] is None
    assert payload["summary"]["failed_cases"] == 1
    assert payload["overall_decision"] == "ng"
    assert payload["cases"][0]["case_id"] == "QA001"
    assert payload["cases"][0]["question"] == "返金できますか"
    assert payload["cases"][0]["ai_answer"] == "返金できます"
    assert payload["cases"][0]["expected_answer"] == "返金条件を案内する"
    assert payload["cases"][0]["expected_evidence"] == ["refund_policy"]
    assert payload["cases"][0]["retrieved_evidence"] == ["refund_policy"]
    assert payload["cases"][0]["judge_fallback_used"] is True
    assert payload["cases"][0]["judge_fallback_reason"] == "parse_error"
    assert payload["cases"][0]["judge_reliability"] == "low"
    assert payload["cases"][0]["needs_human_review"] is True


def test_gate_report_bundle_ci_mode_omits_sensitive_case_content() -> None:
    result = CheckResult(
        run_id="run-ci-redacted",
        current_runs=1,
        baseline_runs=0,
        overall_rate=0.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
        current_records=[
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="run-ci-redacted",
                case_id="QA-secret",
                severity="S1",
                category="policy",
                risk_domain="refund",
                required_action="block",
                passed=False,
                failure_type="keyword_miss",
                failure_category="answer_mismatch",
                reasons=["raw reason with customer secret answer"],
                answer="AI answer with customer secret",
                retrieved_ids=["retrieved-secret-text"],
            )
        ],
        active_cases=[
            QATestCase(
                case_id="QA-secret",
                name="Sensitive refund case",
                question="Question with customer secret?",
                severity="S1",
                expected_answer="Expected answer with customer secret",
                expected_evidence=["expected-secret-evidence"],
                category="policy",
                risk_domain="refund",
                source_doc="C:/internal/customer/refund-policy.md",
            )
        ],
    )
    artifacts = _make_bundle_artifacts(result)
    artifacts = GateReportArtifacts(
        markdown="# Proof Gate Safe Summary\n",
        decision=artifacts.decision,
        history_summary=artifacts.history_summary,
        report_path=artifacts.report_path,
        decision_path=artifacts.decision_path,
        history_summary_path=artifacts.history_summary_path,
        history_path=artifacts.history_path,
        bundle_path=artifacts.bundle_path,
        check_result=result,
        report_mode="ci",
    )

    payload = build_gate_report_bundle_payload(artifacts)
    serialized = json.dumps(payload, ensure_ascii=False)

    assert_gate_report_bundle_contract(payload)
    assert payload["report_mode"] == "ci"
    assert payload["target_docs"] == []
    assert "question" not in payload["cases"][0]
    assert "ai_answer" not in payload["cases"][0]
    assert "expected_answer" not in payload["cases"][0]
    assert "expected_evidence" not in payload["cases"][0]
    assert "retrieved_evidence" not in payload["cases"][0]
    assert "Question with customer secret" not in serialized
    assert "AI answer with customer secret" not in serialized
    assert "Expected answer with customer secret" not in serialized
    assert "retrieved-secret-text" not in serialized
    assert "raw reason with customer secret answer" not in serialized
    assert "C:/internal/customer" not in serialized


def test_check_command_ci_mode_stdout_and_bundle_omit_sensitive_content(capsys) -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-check-ci-report-mode"
    quality_pack = log_dir.parent / f"{uuid.uuid4()}-quality-pack.yml"
    quality_pack.write_text(
        "\n".join(
            [
                "pack:",
                "  client_name: ACME Customer",
                "  app_name: Customer FAQ Bot",
                "  tenant_name: tenant-secret-name",
                "  review_steward: qa-owner@example.test",
                "  change_event: pricing endpoint https://rag.example.test/search",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_result = CheckResult(
        run_id="run-ci-stdout",
        current_runs=1,
        baseline_runs=0,
        overall_rate=0.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
        current_records=[
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="run-ci-stdout",
                case_id="QA-ci",
                severity="S1",
                category="policy",
                risk_domain="refund",
                required_action="block",
                passed=False,
                failure_type="keyword_miss",
                failure_category="answer_mismatch",
                reasons=["stdout raw reason with customer secret answer"],
                answer="stdout customer secret answer",
                retrieved_ids=["stdout-retrieved-secret"],
            )
        ],
        active_cases=[
            QATestCase(
                case_id="QA-ci",
                name="CI case",
                question="stdout customer secret question?",
                severity="S1",
                expected_answer="stdout customer secret expected",
                expected_evidence=["stdout-expected-secret"],
                category="policy",
                risk_domain="refund",
                source_doc="/home/runner/work/customer/source.md",
            )
        ],
        run_provenance={
            "model": "gpt-customer-model",
            "prompt_hash": "hash-safe",
            "endpoint": "https://rag.example.test/search?token=SECRET_TOKEN_ABC",
            "source_path": r"C:\customer\internal\policy.md",
            "doc_snapshot_ids": ["tenant-secret-name"],
        },
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        exit_code = main(
            [
                "check",
                "--log-dir",
                str(log_dir),
                "--report-mode",
                "ci",
                "--quality-pack",
                str(quality_pack),
            ]
        )

    captured = capsys.readouterr()
    bundle_payload = json.loads((log_dir / "gate-report-ci.json").read_text(encoding="utf-8"))
    decision_payload = json.loads((log_dir / "gate-decision.json").read_text(encoding="utf-8"))
    history_payload = json.loads(
        (log_dir / "gate-history-summary.json").read_text(encoding="utf-8")
    )
    combined = (
        captured.out
        + json.dumps(bundle_payload, ensure_ascii=False)
        + json.dumps(decision_payload, ensure_ascii=False)
        + json.dumps(history_payload, ensure_ascii=False)
    )

    assert exit_code == 1
    assert "# Proof Gate Safe Summary" in captured.out
    assert "Saved report to" not in captured.out
    assert "stdout customer secret question" not in combined
    assert "stdout customer secret answer" not in combined
    assert "stdout customer secret expected" not in combined
    assert "stdout-retrieved-secret" not in combined
    assert "stdout raw reason with customer secret answer" not in combined
    assert "/home/runner/work/customer" not in combined
    assert "ACME Customer" not in combined
    assert "Customer FAQ Bot" not in combined
    assert "tenant-secret-name" not in combined
    assert "qa-owner@example.test" not in combined
    assert "https://rag.example.test/search" not in combined
    assert "SECRET_TOKEN_ABC" not in combined
    assert r"C:\customer\internal" not in combined
    assert "gpt-customer-model" not in combined
    assert "hash-safe" in combined
    assert bundle_payload["report_mode"] == "ci"
    assert bundle_payload["artifact_paths"]["report_path"] == "gate-report-ci.md"
    assert bundle_payload["artifact_paths"]["bundle_path"] == "gate-report-ci.json"
    assert bundle_payload["artifact_paths"]["history_path"] == ""
    assert "gate-decisions.jsonl" not in captured.out
    assert "question" not in bundle_payload["cases"][0]
    assert "ai_answer" not in bundle_payload["cases"][0]
    assert "expected_answer" not in bundle_payload["cases"][0]
    assert decision_payload["pack"] is None
    assert history_payload["review_steward"] is None


def test_check_command_rejects_full_report_mode_in_github_actions(monkeypatch, capsys) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    exit_code = main(["check", "--report-mode", "full"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "--report-mode full is not allowed" in captured.err
    assert "sample/mock/dummy data only" in captured.err


def test_gate_command_rejects_full_report_mode_in_github_actions_before_eval(
    monkeypatch, tmp_path, capsys
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    log_dir = tmp_path / "logs"

    with patch("rqg.cli.gate.cmd_eval") as mocked_eval:
        exit_code = main(
            [
                "gate",
                str(tmp_path / "cases.csv"),
                "--log-dir",
                str(log_dir),
                "--report-mode",
                "full",
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 1
    mocked_eval.assert_not_called()
    assert not log_dir.exists()
    assert "--report-mode full is not allowed" in captured.err
    assert "sample/mock/dummy data only" in captured.err


def test_gate_command_rejects_external_endpoint_in_github_actions_before_eval(
    monkeypatch, tmp_path, capsys
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    log_dir = tmp_path / "logs"

    with patch("rqg.cli.gate.cmd_eval") as mocked_eval:
        exit_code = main(
            [
                "gate",
                str(tmp_path / "cases.csv"),
                "--log-dir",
                str(log_dir),
                "--rag-endpoint",
                "https://rag.example.com/search",
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 1
    mocked_eval.assert_not_called()
    assert not log_dir.exists()
    assert "External/customer RAG execution is not allowed" in captured.err
    assert "private runner" in captured.err


def test_eval_command_rejects_external_endpoint_in_github_actions_without_artifacts(
    monkeypatch, tmp_path, capsys
) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    log_dir = tmp_path / "logs"

    exit_code = main(
        [
            "eval",
            str(tmp_path / "cases.csv"),
            "--log-dir",
            str(log_dir),
            "--rag-endpoint",
            "https://rag.example.com/search",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert not log_dir.exists()
    assert "External/customer RAG execution is not allowed" in captured.err
    assert "customer-controlled environment" in captured.err


def test_check_command_defaults_to_ci_report_mode_in_github_actions(monkeypatch, capsys) -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-check-github-actions-default"
    fake_result = CheckResult(
        run_id="run-github-actions-default",
        current_runs=1,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 100.0, True, "1/1")],
    )
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        exit_code = main(["check", "--log-dir", str(log_dir)])

    captured = capsys.readouterr()
    bundle_payload = json.loads((log_dir / "gate-report-ci.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "# Proof Gate Safe Summary" in captured.out
    assert bundle_payload["report_mode"] == "ci"
    assert (log_dir / "gate-report-ci.md").exists()
    assert not (log_dir / "gate-report.md").exists()


def test_ci_history_summary_omits_stale_owner_source_and_notes() -> None:
    payload = {
        "entries": 2,
        "status_mix": {"pass": 1, "warn": 0, "fail": 1},
        "execution_mode": "mock",
        "week_start": "2026-05-11",
        "compare_offset": 1,
        "trend_window": 5,
        "summary_lines": ["secret owner qa-owner source /home/runner/work/customer/policy.md"],
        "comparison": {
            "current_run_id": "run-current",
            "previous_run_id": "run-previous",
            "current_status": "FAIL",
            "previous_status": "PASS",
            "new_reasons": ["answer=secret answer"],
            "resolved_reasons": ["question=secret question"],
            "metric_deltas": [],
            "action_deltas": [],
        },
        "failure_action_coverage": {
            "total_categories": 1,
            "covered_categories": 0,
            "coverage_rate": 0.0,
            "uncovered_categories": [
                {
                    "failure_category": "retrieval_miss",
                    "affected_case_ids": ["ACME-SECRET-CASE"],
                }
            ],
            "window_size": 5,
        },
        "uncovered_categories": [{"affected_case_ids": ["ACME-SECRET-CASE"]}],
        "stale_case_review": {
            "stale_after_days": 30,
            "fresh_case_review_rate": 0.0,
            "fresh_case_count": 0,
            "total_cases": 1,
            "stale_cases_count": 1,
            "owners": [{"owner": "qa-owner@example.test"}],
            "stale_cases": [
                {
                    "case_id": "ACME-SECRET-CASE",
                    "name": "customer case",
                    "owner": "qa-owner@example.test",
                    "reference_value": "/home/runner/work/customer/policy.md",
                    "issue": "notes contain SECRET_TOKEN_ABC",
                }
            ],
        },
        "reliability": {
            "policy_status": "block",
            "fallback_summary": {"chunk_text": "secret evidence"},
        },
        "review_steward": "qa-owner@example.test",
    }

    safe_payload = build_ci_safe_history_summary_payload(payload)
    serialized = json.dumps(safe_payload, ensure_ascii=False)

    for forbidden in [
        "qa-owner",
        "ACME-SECRET-CASE",
        "/home/runner/work/customer",
        "SECRET_TOKEN_ABC",
        "secret evidence",
        "secret answer",
        "secret question",
        "customer case",
    ]:
        assert forbidden not in serialized

    assert safe_payload["stale_case_review"]["stale_cases_count"] == 1
    assert safe_payload["review_steward"] is None


def test_check_command_writes_execution_mode_and_customer_summary(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    fake_result = CheckResult(
        run_id="run-execution-mode",
        current_runs=1,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 100.0, True, "1/1")],
        execution_mode="external_real",
        run_provenance={"prompt_hash": "abc", "model": "gpt-4o-mini"},
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        exit_code = main(["check", "--log-dir", str(log_dir), "--customer-facing"])

    bundle_payload = json.loads((log_dir / "gate-report.json").read_text(encoding="utf-8"))
    customer_summary = (log_dir / "customer-summary.md").read_text(encoding="utf-8")

    assert exit_code == 0
    assert bundle_payload["execution_mode"] == "external_real"
    assert bundle_payload["decision"]["execution_mode"] == "external_real"
    assert bundle_payload["provenance"]["prompt_hash"] == "abc"
    assert "execution_mode: external_real" in customer_summary


def test_check_command_writes_manual_review_and_before_after_artifacts(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    baseline_path = tmp_path / "before.json"
    manual_review_path = tmp_path / "manual-review.json"
    baseline_path.write_text(
        json.dumps(
            {
                "decision": {
                    "run_id": "before-run",
                    "policy_status": "pass",
                    "provenance": {"model": "gpt-4o-mini"},
                },
                "overall_decision": "ok",
                "provenance": {"model": "gpt-4o-mini", "execution_mode": "real"},
                "cases": [{"case_id": "CASE-1", "pass_fail": "pass", "severity": "S1"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manual_review_path.write_text(
        json.dumps(
            {
                "reviews": [
                    {
                        "review_id": "REV-1",
                        "case_id": "CASE-1",
                        "run_id": "after-run",
                        "reviewer": "qa-owner",
                        "review_status": "approved",
                        "review_comment": "checked",
                        "reviewed_at": "2026-05-11T00:00:00Z",
                        "evidence_checked": True,
                        "approval_scope": "case",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    fake_result = CheckResult(
        run_id="after-run",
        current_runs=1,
        baseline_runs=0,
        overall_rate=0.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
        current_records=[
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="after-run",
                case_id="CASE-1",
                severity="S1",
                passed=False,
                failure_type="numeric_mismatch",
                failure_category="synthesis",
            )
        ],
        active_cases=[
            QATestCase(
                case_id="CASE-1",
                name="Case 1",
                question="Q",
                severity="S1",
                expected_answer="7日以内",
                expected_evidence=["policy.md#sec-1"],
            )
        ],
        execution_mode="real",
        run_provenance={"model": "gpt-4.1", "execution_mode": "real"},
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        exit_code = main(
            [
                "check",
                "--log-dir",
                str(log_dir),
                "--manual-review-file",
                str(manual_review_path),
                "--baseline-bundle",
                str(baseline_path),
            ]
        )

    decision_payload = json.loads((log_dir / "gate-decision.json").read_text(encoding="utf-8"))
    comparison_payload = json.loads(
        (log_dir / "before-after-summary.json").read_text(encoding="utf-8")
    )

    assert exit_code == 1
    assert decision_payload["manual_review_summary"]["approved"] == 1
    assert comparison_payload["before_run_id"] == "before-run"
    assert comparison_payload["after_run_id"] == "after-run"
    assert "CASE-1" in comparison_payload["newly_failing_cases"]


def test_build_gate_report_bundle_payload_maps_overall_decision_variants() -> None:
    cases = [
        (
            "ok",
            CheckResult(
                run_id="run-ok",
                current_runs=2,
                baseline_runs=0,
                overall_rate=100.0,
                s1_rate=100.0,
                s1_passed=1,
                s1_total=1,
                thresholds=[ThresholdResult("Overall", 80.0, 100.0, True, "2/2")],
            ),
        ),
        (
            "needs_confirmation",
            CheckResult(
                run_id="run-warn",
                current_runs=2,
                baseline_runs=0,
                overall_rate=100.0,
                s1_rate=100.0,
                s1_passed=1,
                s1_total=1,
                thresholds=[
                    ThresholdResult(
                        "Overall",
                        80.0,
                        85.0,
                        True,
                        "2/2",
                        warn_threshold=90.0,
                        warned=True,
                    )
                ],
            ),
        ),
        (
            "ng",
            CheckResult(
                run_id="run-ng",
                current_runs=2,
                baseline_runs=0,
                overall_rate=50.0,
                s1_rate=0.0,
                s1_passed=0,
                s1_total=1,
                thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
            ),
        ),
    ]

    for expected, result in cases:
        payload = build_gate_report_bundle_payload(_make_bundle_artifacts(result))
        assert payload["overall_decision"] == expected


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


def test_check_command_returns_non_zero_when_policy_status_is_block() -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-check-policy-block"
    fake_result = CheckResult(
        run_id="run-policy-block",
        current_runs=1,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[
            ThresholdResult("Overall pass rate", 80.0, 100.0, True, "1/1"),
        ],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-policy-block"):
            exit_code = main(["check", "--log-dir", str(log_dir)])

    payload = json.loads((log_dir / "gate-decision.json").read_text(encoding="utf-8"))
    assert payload["policy_status"] == "block"
    assert exit_code == 1


def test_check_command_returns_zero_when_policy_status_is_pass() -> None:
    log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-check-policy-pass"
    fake_result = CheckResult(
        run_id="run-policy-pass",
        current_runs=1,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[
            ThresholdResult("S1 pass rate", 100.0, 100.0, True, "1/1"),
        ],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-policy-pass"):
            exit_code = main(["check", "--log-dir", str(log_dir)])

    payload = json.loads((log_dir / "gate-decision.json").read_text(encoding="utf-8"))
    assert payload["policy_status"] == "pass"
    assert exit_code == 0


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


def test_check_command_gate_report_includes_recent_history_summary(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
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
