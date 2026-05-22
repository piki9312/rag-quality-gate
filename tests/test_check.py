"""Tests for gate check (check.py)."""

from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from rqg.cli.check import cmd_check
from rqg.domain import GateDecision, GateNextAction
from rqg.quality.check import (
    CheckResult,
    GateConfig,
    ThresholdResult,
    build_gate_decision,
    load_failure_actions_from_quality_pack,
    load_records,
    map_overall_decision,
    render_customer_summary_markdown,
    render_gate_markdown,
    run_check,
)
from rqg.quality.models import QARunRecord, QATestCase
from rqg.quality.staleness import CaseStalenessItem

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def gate_config():
    return GateConfig(s1_pass_rate=100.0, overall_pass_rate=80.0)


@pytest.fixture()
def log_dir_with_records(tmp_path):
    """Create a JSONL log dir with mixed pass/fail data."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    jsonl = log_dir / f"{today}.jsonl"

    records = [
        QARunRecord(
            timestamp=datetime.now(timezone.utc),
            run_id="r1",
            case_id="QA001",
            severity="S1",
            passed=True,
        ),
        QARunRecord(
            timestamp=datetime.now(timezone.utc),
            run_id="r1",
            case_id="QA002",
            severity="S2",
            passed=True,
        ),
        QARunRecord(
            timestamp=datetime.now(timezone.utc),
            run_id="r1",
            case_id="QA003",
            severity="S2",
            passed=False,
            failure_type="keyword_miss",
            failure_category="synthesis",
        ),
    ]

    with open(jsonl, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(rec.model_dump_json() + "\n")

    return str(log_dir)


def _write_single_pass_log(log_dir: Path, *, run_id: str = "run-stage") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    record = QARunRecord(
        timestamp=datetime.now(timezone.utc),
        run_id=run_id,
        case_id="QA001",
        severity="S1",
        passed=True,
    )
    (log_dir / f"{today}.jsonl").write_text(record.model_dump_json() + "\n", encoding="utf-8")


def _run_cmd_check_for_stage(
    tmp_path: Path,
    *,
    review_stage: str | None = None,
    quality_pack_text: str | None = None,
    gate_text: str | None = None,
    change_event_text: str | None = None,
) -> tuple[int, dict[str, object], Path]:
    log_dir = tmp_path / f"logs-{uuid.uuid4().hex[:8]}"
    _write_single_pass_log(log_dir)
    quality_pack_path = tmp_path / f"quality-pack-{uuid.uuid4().hex[:8]}.yml"
    quality_pack_path.write_text(
        quality_pack_text or "pack:\n  pack_name: stage-test\n",
        encoding="utf-8",
    )
    gate_path = tmp_path / f"gate-{uuid.uuid4().hex[:8]}.yml"
    gate_path.write_text(
        gate_text or "thresholds:\n  s1_pass_rate: 100.0\n  overall_pass_rate: 80.0\n",
        encoding="utf-8",
    )
    change_event_path = None
    if change_event_text is not None:
        change_event_path = tmp_path / f"change-event-{uuid.uuid4().hex[:8]}.yml"
        change_event_path.write_text(change_event_text, encoding="utf-8")

    exit_code = cmd_check(
        SimpleNamespace(
            log_dir=str(log_dir),
            config=str(gate_path),
            days=1,
            baseline_dir=None,
            baseline_days=7,
            cases_file=None,
            quality_pack=str(quality_pack_path),
            s1_threshold=100.0,
            overall_threshold=80.0,
            max_overall_drop_pct=None,
            max_s1_drop_pct=None,
            aggregation_policy=None,
            output_file=None,
            decision_file=None,
            bundle_file=None,
            report_mode="ci",
            customer_facing=False,
            allow_simulation_output=False,
            strict_s1_governance=False,
            change_event_file=str(change_event_path) if change_event_path else None,
            review_stage=review_stage,
            manual_review_file=None,
            baseline_bundle=None,
            warn_exit_code=0,
            append_history=False,
            notifications_enabled=False,
        )
    )
    bundle_path = log_dir / "gate-report-ci.json"
    payload = json.loads(bundle_path.read_text(encoding="utf-8")) if bundle_path.exists() else {}
    return exit_code, payload, log_dir


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


class TestReviewStageInputs:
    def test_cli_review_stage_pre_delivery_is_written_to_review_packet(self, tmp_path, capsys):
        exit_code, payload, _ = _run_cmd_check_for_stage(
            tmp_path,
            review_stage="pre_delivery",
        )

        assert exit_code == 0
        assert payload["review_packet"]["review_stage"] == "pre_delivery"
        assert payload["customer_review_markdown"].startswith(
            "# AI回答品質診断レポート"
        )

    def test_cli_review_stage_post_delivery_change_is_written_to_review_packet(
        self, tmp_path, capsys
    ):
        exit_code, payload, _ = _run_cmd_check_for_stage(
            tmp_path,
            review_stage="post_delivery_change",
        )

        assert exit_code == 0
        assert payload["review_packet"]["review_stage"] == "post_delivery_change"
        assert payload["customer_review_markdown"].startswith("# 変更後品質確認レポート")

    def test_pack_metadata_review_stage_is_used(self, tmp_path, capsys):
        exit_code, payload, _ = _run_cmd_check_for_stage(
            tmp_path,
            quality_pack_text="pack:\n  pack_name: stage-test\n  review_stage: monthly_review\n",
        )

        assert exit_code == 0
        assert payload["review_packet"]["review_stage"] == "monthly_review"
        assert payload["customer_review_markdown"].startswith("# 月次AI回答品質レビュー")

    def test_cli_review_stage_overrides_pack_metadata(self, tmp_path, capsys):
        exit_code, payload, _ = _run_cmd_check_for_stage(
            tmp_path,
            review_stage="pre_delivery",
            quality_pack_text="pack:\n  pack_name: stage-test\n  review_stage: monthly_review\n",
        )

        assert exit_code == 0
        assert payload["review_packet"]["review_stage"] == "pre_delivery"

    def test_gate_yml_review_stage_is_used_after_quality_pack(self, tmp_path, capsys):
        exit_code, payload, _ = _run_cmd_check_for_stage(
            tmp_path,
            gate_text=(
                "review_stage: monthly_review\n"
                "thresholds:\n  s1_pass_rate: 100.0\n  overall_pass_rate: 80.0\n"
            ),
        )

        assert exit_code == 0
        assert payload["review_packet"]["review_stage"] == "monthly_review"

    def test_change_event_review_stage_is_used_after_pack_and_gate(self, tmp_path, capsys):
        exit_code, payload, _ = _run_cmd_check_for_stage(
            tmp_path,
            change_event_text=(
                "change_id: change-stage\n"
                "change_type: document_update\n"
                "review_stage: post_delivery_change\n"
            ),
        )

        assert exit_code == 0
        assert payload["review_packet"]["review_stage"] == "post_delivery_change"

    def test_invalid_review_stage_fails_without_traceback(self, tmp_path, capsys):
        exit_code, payload, _ = _run_cmd_check_for_stage(
            tmp_path,
            quality_pack_text="pack:\n  pack_name: stage-test\n  review_stage: shipment\n",
        )
        captured = capsys.readouterr()

        assert exit_code == 1
        assert payload == {}
        assert "Invalid review_stage 'shipment'" in captured.err
        assert "Traceback" not in captured.err


class TestGateConfig:
    def test_defaults(self):
        cfg = GateConfig()
        assert cfg.s1_pass_rate == 100.0
        assert cfg.overall_pass_rate == 80.0
        assert cfg.aggregation_policy == "latest_run"

    def test_from_yaml(self, tmp_path):
        yaml_path = tmp_path / "gate.yml"
        yaml_path.write_text(
            (
                "thresholds:\n"
                "  s1_pass_rate: 95.0\n"
                "  overall_pass_rate: 75.0\n"
                "  max_overall_drop_pct: 10.0\n"
                "  max_s1_drop_pct: 5.0\n"
                "  case_staleness_days: 30\n"
                "  min_fresh_case_review_rate: 90.0\n"
                "  fresh_case_review_rate_warn: 100.0\n"
                "  min_evidence_recall: 90.0\n"
                "  aggregation_policy: window\n"
            ),
            encoding="utf-8",
        )
        cfg = GateConfig.from_yaml(str(yaml_path))
        assert cfg.s1_pass_rate == 95.0
        assert cfg.overall_pass_rate == 75.0
        assert cfg.max_overall_drop_pct == 10.0
        assert cfg.max_s1_drop_pct == 5.0
        assert cfg.case_staleness_days == 30
        assert cfg.min_fresh_case_review_rate == 90.0
        assert cfg.fresh_case_review_rate_warn == 100.0
        assert cfg.min_evidence_recall == 90.0
        assert cfg.aggregation_policy == "window"

    def test_from_yaml_reads_expected_evidence_hit_rate(self):
        yaml_path = Path("tests/.tmp") / f"{uuid.uuid4()}-gate.yml"
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        yaml_path.write_text(
            "thresholds:\n  expected_evidence_hit_rate: 75.0\n",
            encoding="utf-8",
        )

        cfg = GateConfig.from_yaml(str(yaml_path))

        assert cfg.expected_evidence_hit_rate_threshold == 75.0

    def test_from_yaml_reads_deprecated_retrieval_precision_alias(self):
        yaml_path = Path("tests/.tmp") / f"{uuid.uuid4()}-gate.yml"
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        yaml_path.write_text(
            "thresholds:\n  retrieval_precision: 65.0\n",
            encoding="utf-8",
        )

        cfg = GateConfig.from_yaml(str(yaml_path))

        assert cfg.expected_evidence_hit_rate_threshold == 65.0

    def test_load_failure_actions_from_quality_pack(self, tmp_path):
        quality_pack = tmp_path / "quality-pack.yml"
        quality_pack.write_text(
            """
common_failure_patterns:
  - name: retrieval_miss
    first_action: Review chunking/retrieval settings
  - name: synthesis
    action: Refresh expected evidence and keywords
""".strip(),
            encoding="utf-8",
        )

        actions = load_failure_actions_from_quality_pack(quality_pack)
        assert actions["retrieval_miss"] == "Review chunking/retrieval settings"
        assert actions["synthesis"] == "Refresh expected evidence and keywords"


class TestLoadRecords:
    def test_load(self, log_dir_with_records):
        records = load_records(log_dir_with_records)
        assert len(records) == 3

    def test_empty_dir(self, tmp_path):
        assert load_records(str(tmp_path / "nonexistent")) == []

    def test_ignores_non_eval_jsonl_files(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        # Non-eval JSONL artifact should be ignored.
        (log_dir / "gate-decisions.jsonl").write_text('{"run_id":"gate-only"}\n', encoding="utf-8")

        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        eval_jsonl = log_dir / f"{today}.jsonl"
        record = QARunRecord(
            timestamp=datetime.now(timezone.utc),
            run_id="r-test",
            case_id="QA001",
            severity="S1",
            passed=True,
        )
        eval_jsonl.write_text(record.model_dump_json() + "\n", encoding="utf-8")

        records = load_records(str(log_dir))
        assert len(records) == 1
        assert records[0].run_id == "r-test"


class TestRunCheck:
    def test_gate_pass(self, log_dir_with_records, gate_config):
        # 2/3 pass → 66.7% < 80%, but S1 is 100%
        gate_config.overall_pass_rate = 60.0
        result = run_check(log_dir_with_records, gate_config, days=1)
        assert result.current_runs == 3
        assert result.s1_rate == 100.0
        assert result.gate_passed is True

    def test_gate_fail_overall(self, log_dir_with_records, gate_config):
        result = run_check(log_dir_with_records, gate_config, days=1)
        # 66.7% < 80%
        assert result.gate_passed is False
        assert result.failure_categories.get("synthesis") == 1


def test_render_gate_markdown_includes_recent_history_summary_and_coverage() -> None:
    previous_decision = GateDecision(
        run_id="run-001",
        status="warn",
        reasons=["WARN Overall pass rate: 75.0 < warn threshold 85.0"],
        metrics={
            "overall_pass_rate": 75.0,
            "s1_pass_rate": 100.0,
            "current_runs": 4.0,
        },
        next_actions=[
            GateNextAction(
                failure_category="retrieval_miss",
                count=1,
                action="Review retrieval settings",
                owner="T.B.D.",
                due="T.B.D.",
                affected_case_ids=["QA-1"],
            )
        ],
        created_at=datetime(2026, 4, 20, 0, 0, tzinfo=timezone.utc),
    )
    result = CheckResult(
        run_id="run-002",
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

    markdown = render_gate_markdown(
        result,
        failure_actions={"retrieval_miss": "Review retrieval settings"},
        history_decisions=[
            previous_decision,
            build_gate_decision(
                result,
                failure_actions={"retrieval_miss": "Review retrieval settings"},
            ),
        ],
    )

    assert "### Recent History Summary" in markdown
    assert "Compared runs: run-001 -> run-002" in markdown
    assert "Failure action coverage (last 2): 1/2 categories (50.0%)" in markdown
    assert "Uncovered categories: unknown (1 case)" in markdown

    def test_latest_run_policy_uses_only_newest_run(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        records = [
            QARunRecord(
                timestamp=now - timedelta(minutes=30),
                run_id="run-old",
                case_id="QA001",
                severity="S2",
                passed=False,
                failure_type="keyword_miss",
                failure_category="synthesis",
            ),
            QARunRecord(
                timestamp=now - timedelta(minutes=5),
                run_id="run-new",
                case_id="QA001",
                severity="S2",
                passed=True,
            ),
        ]
        (log_dir / f"{today}.jsonl").write_text(
            "\n".join(record.model_dump_json() for record in records) + "\n",
            encoding="utf-8",
        )

        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=100.0)
        result = run_check(str(log_dir), cfg, days=1)

        assert result.aggregation_policy == "latest_run"
        assert result.run_id == "run-new"
        assert result.current_runs == 1
        assert result.gate_passed is True

    def test_window_policy_uses_all_runs_in_window(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        records = [
            QARunRecord(
                timestamp=now - timedelta(minutes=30),
                run_id="run-old",
                case_id="QA001",
                severity="S2",
                passed=False,
                failure_type="keyword_miss",
                failure_category="synthesis",
            ),
            QARunRecord(
                timestamp=now - timedelta(minutes=5),
                run_id="run-new",
                case_id="QA001",
                severity="S2",
                passed=True,
            ),
        ]
        (log_dir / f"{today}.jsonl").write_text(
            "\n".join(record.model_dump_json() for record in records) + "\n",
            encoding="utf-8",
        )

        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=100.0, aggregation_policy="window")
        result = run_check(str(log_dir), cfg, days=1)

        assert result.aggregation_policy == "window"
        assert result.current_runs == 2
        assert result.gate_passed is False

    def test_no_data_fails(self, tmp_path, gate_config):
        result = run_check(str(tmp_path / "empty"), gate_config, days=1)
        assert result.current_runs == 0
        assert result.gate_passed is False

    def test_cases_file_filters_non_active_records(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        records = [
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="r1",
                case_id="ACTIVE001",
                severity="S1",
                passed=True,
            ),
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="r1",
                case_id="DRAFT001",
                severity="S2",
                passed=False,
                failure_type="keyword_miss",
                failure_category="synthesis",
            ),
        ]
        (log_dir / f"{today}.jsonl").write_text(
            "\n".join(record.model_dump_json() for record in records) + "\n",
            encoding="utf-8",
        )

        cases_file = tmp_path / "cases.csv"
        with open(cases_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "case_id",
                    "name",
                    "status",
                    "severity",
                    "question",
                    "expected_answer",
                    "min_case_score",
                ],
            )
            writer.writeheader()
            writer.writerows(
                [
                    {
                        "case_id": "ACTIVE001",
                        "name": "active",
                        "status": "active",
                        "severity": "S1",
                        "question": "Q?",
                        "expected_answer": "A",
                        "min_case_score": "100",
                    },
                    {
                        "case_id": "DRAFT001",
                        "name": "draft",
                        "status": "draft",
                        "severity": "S2",
                        "question": "Q?",
                        "expected_answer": "A",
                        "min_case_score": "100",
                    },
                ]
            )

        cfg = GateConfig(s1_pass_rate=100.0, overall_pass_rate=100.0)
        result = run_check(str(log_dir), cfg, days=1, cases_file=str(cases_file))

        assert result.current_runs == 1
        assert result.overall_rate == 100.0
        assert result.gate_passed is True
        assert result.failure_categories == {}
        assert [threshold.name for threshold in result.case_thresholds] == ["case:ACTIVE001"]

    def test_regression_drop_fails_when_drop_exceeds_threshold(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        now = datetime.now(timezone.utc)
        baseline_day = (now - timedelta(days=2)).strftime("%Y%m%d")
        current_day = now.strftime("%Y%m%d")

        baseline_record = QARunRecord(
            timestamp=now - timedelta(days=2, hours=1),
            run_id="baseline-1",
            case_id="QA001",
            severity="S1",
            passed=True,
        )
        current_record = QARunRecord(
            timestamp=now - timedelta(hours=1),
            run_id="current-1",
            case_id="QA001",
            severity="S1",
            passed=False,
        )

        (log_dir / f"{baseline_day}.jsonl").write_text(
            baseline_record.model_dump_json() + "\n",
            encoding="utf-8",
        )
        (log_dir / f"{current_day}.jsonl").write_text(
            current_record.model_dump_json() + "\n",
            encoding="utf-8",
        )

        cfg = GateConfig(
            s1_pass_rate=0.0,
            overall_pass_rate=0.0,
            max_overall_drop_pct=10.0,
            max_s1_drop_pct=10.0,
        )
        result = run_check(str(log_dir), cfg, days=1, baseline_days=7)

        assert result.gate_passed is False
        assert result.baseline_overall_rate == 100.0
        assert result.overall_drop == 100.0
        assert any(
            t.name == "Overall pass rate drop" and t.passed is False for t in result.thresholds
        )
        assert any(t.name == "S1 pass rate drop" and t.passed is False for t in result.thresholds)

    def test_regression_drop_fails_without_baseline_data(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        now = datetime.now(timezone.utc)
        current_day = now.strftime("%Y%m%d")
        current_record = QARunRecord(
            timestamp=now - timedelta(hours=1),
            run_id="current-only",
            case_id="QA001",
            severity="S1",
            passed=True,
        )
        (log_dir / f"{current_day}.jsonl").write_text(
            current_record.model_dump_json() + "\n",
            encoding="utf-8",
        )

        cfg = GateConfig(
            s1_pass_rate=0.0,
            overall_pass_rate=0.0,
            max_overall_drop_pct=5.0,
        )
        result = run_check(str(log_dir), cfg, days=1, baseline_days=7)

        assert result.gate_passed is False
        assert any(
            t.name == "Overall pass rate drop"
            and t.passed is False
            and "No baseline run data found" in t.detail
            for t in result.thresholds
        )

    def test_observed_metrics_include_judge_relevance_and_evidence_recall(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        records = [
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,
                faithfulness_score=0.9,
                judge_relevance=0.8,
                evidence_recall=1.0,
            ),
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA002",
                severity="S2",
                passed=True,
                faithfulness_score=0.7,
                judge_relevance=0.6,
                evidence_recall=0.5,
            ),
        ]
        (log_dir / f"{today}.jsonl").write_text(
            "\n".join(record.model_dump_json() for record in records) + "\n",
            encoding="utf-8",
        )

        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=0.0)
        result = run_check(str(log_dir), cfg, days=1)
        decision = build_gate_decision(result)

        assert result.avg_faithfulness == pytest.approx(80.0)
        assert result.avg_judge_relevance == pytest.approx(70.0)
        assert result.avg_evidence_recall == pytest.approx(75.0)
        assert result.faithfulness_scored == 2
        assert result.judge_relevance_scored == 2
        assert result.evidence_recall_scored == 2
        assert decision.metrics["avg_judge_relevance"] == pytest.approx(70.0)
        assert decision.metrics["avg_evidence_recall"] == pytest.approx(75.0)
        assert decision.metrics["avg_expected_evidence_recall"] == pytest.approx(75.0)
        assert decision.metrics["judge_relevance_scored_runs"] == 2.0
        assert decision.metrics["evidence_recall_scored_runs"] == 2.0
        assert decision.metrics["expected_evidence_recall_scored_runs"] == 2.0


class TestCheckResult:
    def test_gate_passed_property(self):
        result = CheckResult(
            run_id="run-001",
            current_runs=10,
            baseline_runs=0,
            overall_rate=90.0,
            s1_rate=100.0,
            s1_passed=3,
            s1_total=3,
            thresholds=[
                ThresholdResult("S1", 100.0, 100.0, True),
                ThresholdResult("Overall", 80.0, 90.0, True),
            ],
        )
        assert result.gate_passed is True

    def test_build_gate_decision_includes_structured_next_actions(self):
        result = CheckResult(
            run_id="run-structured-actions",
            current_runs=5,
            baseline_runs=3,
            overall_rate=60.0,
            s1_rate=50.0,
            s1_passed=1,
            s1_total=2,
            thresholds=[
                ThresholdResult("S1 pass rate", 100.0, 50.0, False, "1/2"),
            ],
            failure_categories={"retrieval_miss": 2, "other": 1},
        )

        decision = build_gate_decision(
            result,
            failure_actions={"retrieval_miss": "Review retrieval settings"},
        )

        actions = {item.failure_category: item for item in decision.next_actions}
        assert actions["retrieval_miss"].count == 2
        assert actions["retrieval_miss"].action == "Review retrieval settings"
        assert actions["other"].count == 1
        assert actions["other"].action == "Define next action in weekly review issue"

    def test_gate_decision_includes_affected_case_ids(self):
        result = CheckResult(
            run_id="run-case-ids",
            current_runs=5,
            baseline_runs=0,
            overall_rate=60.0,
            s1_rate=50.0,
            s1_passed=1,
            s1_total=2,
            thresholds=[
                ThresholdResult("S1 pass rate", 100.0, 50.0, False, "1/2"),
            ],
            failure_categories={"synthesis": 3, "retrieval_miss": 1},
            failure_case_ids={
                "synthesis": ["QA001", "QA003", "QA005"],
                "retrieval_miss": ["QA009"],
            },
        )

        decision = build_gate_decision(
            result,
            failure_actions={"synthesis": "Check answer keywords"},
        )

        actions = {item.failure_category: item for item in decision.next_actions}
        assert actions["synthesis"].affected_case_ids == ["QA001", "QA003", "QA005"]
        assert actions["synthesis"].action == "Check answer keywords"
        assert actions["retrieval_miss"].affected_case_ids == ["QA009"]

    def test_gate_decision_empty_case_ids_when_not_provided(self):
        result = CheckResult(
            run_id="run-no-case-ids",
            current_runs=3,
            baseline_runs=0,
            overall_rate=66.7,
            s1_rate=100.0,
            s1_passed=1,
            s1_total=1,
            thresholds=[
                ThresholdResult("Overall", 80.0, 66.7, False, "2/3"),
            ],
            failure_categories={"unknown": 1},
        )

        decision = build_gate_decision(result)
        assert decision.next_actions[0].affected_case_ids == []

    def test_build_gate_decision_includes_reliability_signals(self):
        result = CheckResult(
            run_id="run-reliability",
            current_runs=2,
            baseline_runs=0,
            overall_rate=100.0,
            s1_rate=100.0,
            s1_passed=1,
            s1_total=1,
            judge_fallback_count=1,
            judge_failure_types={"parse": 1},
            judge_reliability="low",
            embedding_fallback_count=1,
            embedding_fallback_used=True,
            embedding_fallback_reason="dependency_missing",
            needs_human_review=True,
        )

        decision = build_gate_decision(result)

        assert decision.judge_fallback_used is True
        assert decision.judge_failure_types == {"parse": 1}
        assert decision.judge_reliability == "low"
        assert decision.embedding_fallback_used is True
        assert decision.needs_human_review is True
        assert any(action.failure_category == "human_review" for action in decision.next_actions)

    def test_policy_status_blocks_s1_failure(self):
        result = CheckResult(
            run_id="run-s1-block",
            current_runs=2,
            baseline_runs=0,
            overall_rate=50.0,
            s1_rate=0.0,
            s1_passed=0,
            s1_total=1,
            thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
        )

        decision = build_gate_decision(result)

        assert decision.policy_status == "block"
        assert decision.status == "fail"

    def test_policy_status_warns_for_s2_only_warning(self):
        result = CheckResult(
            run_id="run-s2-warn",
            current_runs=2,
            baseline_runs=0,
            overall_rate=100.0,
            s1_rate=100.0,
            s1_passed=1,
            s1_total=1,
            thresholds=[
                ThresholdResult(
                    "Overall pass rate",
                    80.0,
                    100.0,
                    True,
                    "2/2",
                    warn_threshold=95.0,
                    warned=True,
                )
            ],
        )

        decision = build_gate_decision(result)

        assert decision.policy_status == "warn"

    def test_policy_status_routes_judge_fallback_to_human_review(self):
        result = CheckResult(
            run_id="run-fallback-review",
            current_runs=2,
            baseline_runs=0,
            overall_rate=100.0,
            s1_rate=100.0,
            s1_passed=1,
            s1_total=1,
            judge_fallback_count=1,
            needs_human_review=True,
        )

        decision = build_gate_decision(result)

        assert decision.policy_status == "needs_human_review"
        assert decision.needs_human_review is True

    def test_policy_status_routes_overall_threshold_fail_without_s1_to_human_review(self):
        result = CheckResult(
            run_id="run-overall-review",
            current_runs=3,
            baseline_runs=0,
            overall_rate=66.7,
            s1_rate=100.0,
            s1_passed=1,
            s1_total=1,
            thresholds=[
                ThresholdResult("S1 pass rate", 100.0, 100.0, True, "1/1"),
                ThresholdResult("Overall pass rate", 80.0, 66.7, False, "2/3"),
            ],
        )

        decision = build_gate_decision(result)

        assert decision.status == "fail"
        assert decision.policy_status == "needs_human_review"
        assert map_overall_decision(result) == "needs_confirmation"

    def test_policy_status_routes_s2_only_fail_to_human_review(self):
        result = CheckResult(
            run_id="run-s2-review",
            current_runs=2,
            baseline_runs=0,
            overall_rate=50.0,
            s1_rate=100.0,
            s1_passed=1,
            s1_total=1,
            thresholds=[
                ThresholdResult("S1 pass rate", 100.0, 100.0, True, "1/1"),
                ThresholdResult("Overall pass rate", 80.0, 50.0, False, "1/2"),
            ],
            current_records=[
                QARunRecord(
                    timestamp=datetime.now(timezone.utc),
                    run_id="run-s2-review",
                    case_id="QA-S1",
                    severity="S1",
                    passed=True,
                ),
                QARunRecord(
                    timestamp=datetime.now(timezone.utc),
                    run_id="run-s2-review",
                    case_id="QA-S2",
                    severity="S2",
                    passed=False,
                    failure_type="keyword_miss",
                    failure_category="synthesis",
                ),
            ],
        )

        decision = build_gate_decision(result)

        assert decision.status == "fail"
        assert decision.policy_status == "needs_human_review"
        assert map_overall_decision(result) == "needs_confirmation"

    def test_build_gate_decision_preserves_closing_parentheses_in_reasons(self):
        result = CheckResult(
            run_id="run-reason-format",
            current_runs=2,
            baseline_runs=0,
            overall_rate=0.0,
            s1_rate=0.0,
            s1_passed=0,
            s1_total=1,
            thresholds=[
                ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1"),
                ThresholdResult("Overall pass rate", 85.0, 0.0, False, "0/2"),
                ThresholdResult("Avg expected evidence recall", 80.0, 0.0, False, "2 scored"),
            ],
            case_thresholds=[
                ThresholdResult(
                    "case:VPOC001",
                    100.0,
                    0.0,
                    False,
                    "Password reset escalation",
                )
            ],
        )

        decision = build_gate_decision(result)

        assert decision.reasons == [
            "S1 pass rate: 0.0 < 100.0 (0/1)",
            "Overall pass rate: 0.0 < 85.0 (0/2)",
            "Avg expected evidence recall: 0.0 < 80.0 (2 scored)",
            "case:VPOC001: 0.0 < 100.0 (Password reset escalation)",
        ]


class TestRenderMarkdown:
    def test_pass_rendering(self):
        result = CheckResult(
            run_id="run-001",
            current_runs=10,
            baseline_runs=50,
            overall_rate=90.0,
            s1_rate=100.0,
            s1_passed=3,
            s1_total=3,
            thresholds=[
                ThresholdResult("S1", 100.0, 100.0, True, "3/3"),
                ThresholdResult("Overall", 80.0, 90.0, True, "9/10"),
            ],
        )
        md = render_gate_markdown(result)
        assert "PASS" in md
        assert "S1" in md
        assert "### Executive Summary" in md
        assert (
            "Production promotion: Recommended. This pack meets the configured gate thresholds."
            in md
        )
        assert "Gate status: PASS" in md
        assert "S1 pass rate: 100.0% (0 S1 failures)" in md
        assert "Overall pass rate: 90.0%" in md
        assert "Main failure category: None" in md
        assert "Recommended next action: No immediate action required." in md

    def test_rendering_starts_with_customer_report_sections(self):
        result = CheckResult(
            run_id="run-customer",
            current_runs=2,
            baseline_runs=1,
            overall_rate=100.0,
            s1_rate=100.0,
            s1_passed=1,
            s1_total=1,
            thresholds=[ThresholdResult("Overall", 80.0, 100.0, True, "2/2")],
        )

        md = render_gate_markdown(result)

        assert md.startswith("# Proof Gate 実行レポート")
        assert "## 1. 本番反映判定" in md
        assert "## 4. 実行結果サマリ" in md
        assert "## 8. 月額Monitorで継続確認すべき項目" in md
        assert "## 9. 運用向け詳細" in md
        assert "## RAG Quality Gate: PASS" in md

    def test_fail_rendering(self):
        result = CheckResult(
            run_id="run-001",
            current_runs=10,
            baseline_runs=0,
            overall_rate=60.0,
            s1_rate=50.0,
            s1_passed=1,
            s1_total=2,
            thresholds=[
                ThresholdResult("S1", 100.0, 50.0, False, "1/2"),
            ],
            failure_categories={"retrieval_miss": 2, "synthesis": 1},
        )
        md = render_gate_markdown(
            result,
            failure_actions={"retrieval_miss": "Review retrieval settings"},
        )
        assert "FAIL" in md
        assert "Failure Categories" in md
        assert "retrieval_miss" in md
        assert (
            "Production promotion: Not recommended. This pack should not be promoted to production."
            in md
        )
        assert "Gate status: FAIL" in md
        assert "S1 pass rate: 50.0% (1 S1 failure)" in md
        assert "Overall pass rate: 60.0%" in md
        assert "Main failure category: retrieval_miss (2 cases)" in md
        assert "Recommended next action: Review retrieval settings" in md

    def test_render_gate_markdown_includes_aggregation_policy(self, log_dir_with_records):
        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=0.0)
        result = run_check(log_dir_with_records, cfg, days=1)
        markdown = render_gate_markdown(result)
        assert "- Aggregation Policy: latest_run" in markdown

    def test_fail_rendering_with_next_actions(self):
        result = CheckResult(
            run_id="run-002",
            current_runs=8,
            baseline_runs=0,
            overall_rate=62.5,
            s1_rate=50.0,
            s1_passed=1,
            s1_total=2,
            thresholds=[ThresholdResult("S1", 100.0, 50.0, False, "1/2")],
            failure_categories={"retrieval_miss": 2, "unknown": 1},
            failure_case_ids={
                "retrieval_miss": ["QA001", "QA005"],
                "unknown": ["QA009"],
            },
        )

        md = render_gate_markdown(
            result,
            failure_actions={"retrieval_miss": "Review retrieval settings"},
        )

        assert "Next Actions" in md
        assert "Affected Cases" in md
        assert "QA001, QA005" in md
        assert "QA009" in md
        assert "Review retrieval settings" in md
        assert "Define next action in weekly review issue" in md
        assert "T.B.D." in md

    def test_rendering_orders_s1_failures_first_in_customer_sections(self):
        now = datetime.now(timezone.utc)
        result = CheckResult(
            run_id="run-ordering",
            current_runs=3,
            baseline_runs=0,
            overall_rate=33.3,
            s1_rate=0.0,
            s1_passed=0,
            s1_total=1,
            thresholds=[ThresholdResult("S1", 100.0, 0.0, False, "0/1")],
            current_records=[
                QARunRecord(
                    timestamp=now,
                    run_id="run-ordering",
                    case_id="QA-S2",
                    severity="S2",
                    category="retrieval",
                    risk_domain="ops",
                    passed=False,
                    failure_type="keyword_miss",
                    failure_category="retrieval_miss",
                    reasons=["missing evidence"],
                ),
                QARunRecord(
                    timestamp=now,
                    run_id="run-ordering",
                    case_id="QA-S1",
                    severity="S1",
                    category="policy",
                    risk_domain="refund",
                    passed=False,
                    failure_type="policy_miss",
                    failure_category="policy_gap",
                    reasons=["wrong escalation"],
                ),
                QARunRecord(
                    timestamp=now,
                    run_id="run-ordering",
                    case_id="QA-PASS",
                    severity="S2",
                    category="faq",
                    risk_domain="general",
                    passed=True,
                ),
            ],
            active_cases=[
                QATestCase(
                    case_id="QA-S2",
                    name="S2 retrieval miss",
                    question="詳細は?",
                    severity="S2",
                    expected_answer="evidence",
                    expected_evidence=["doc-s2"],
                    category="retrieval",
                    risk_domain="ops",
                ),
                QATestCase(
                    case_id="QA-S1",
                    name="S1 policy miss",
                    question="返金条件は?",
                    severity="S1",
                    expected_answer="policy",
                    expected_evidence=["doc-s1"],
                    category="policy",
                    risk_domain="refund",
                ),
                QATestCase(
                    case_id="QA-PASS",
                    name="Passing case",
                    question="営業時間は?",
                    severity="S2",
                    expected_answer="hours",
                    expected_evidence=["doc-pass"],
                    category="faq",
                    risk_domain="general",
                ),
            ],
        )

        md = render_gate_markdown(
            result,
            failure_actions={
                "retrieval_miss": "Review retrieval settings",
                "policy_gap": "Fix the policy answer before release",
            },
        )

        assert "## 5. S1重大失敗一覧" in md
        assert md.index("## 5. S1重大失敗一覧") < md.index("## 6. ケース別結果")
        assert "## 8. 月額Monitorで継続確認すべき項目" in md
        assert "FAQ・規約・料金表の更新後にS1ケースを再実行する" in md
        assert md.index("QA-S1") < md.index("QA-S2")

    def test_customer_summary_includes_simulation_warning_and_execution_mode(self):
        result = CheckResult(
            run_id="run-sim",
            current_runs=1,
            baseline_runs=0,
            overall_rate=100.0,
            s1_rate=100.0,
            s1_passed=1,
            s1_total=1,
            thresholds=[ThresholdResult("Overall", 80.0, 100.0, True, "1/1")],
            execution_mode="mock",
        )

        md = render_customer_summary_markdown(result, report_mode="redacted")

        assert "SIMULATION ONLY" in md
        assert "execution_mode: mock" in md
        assert "実システム品質を証明するものではありません" in md

    def test_rendering_includes_observed_metrics(self):
        result = CheckResult(
            run_id="run-observed",
            current_runs=4,
            baseline_runs=0,
            overall_rate=75.0,
            s1_rate=100.0,
            s1_passed=1,
            s1_total=1,
            thresholds=[ThresholdResult("Overall", 70.0, 75.0, True, "3/4")],
            avg_faithfulness=82.0,
            faithfulness_scored=4,
            avg_judge_relevance=78.0,
            judge_relevance_scored=3,
            avg_evidence_recall=66.0,
            evidence_recall_scored=2,
        )

        md = render_gate_markdown(result)

        assert "Observed Metrics" in md
        assert "Avg judge relevance" in md
        assert "Avg expected evidence recall" in md
        assert "Gate Policy / 顧客向け判定ルール" in md
        assert "全回答の完全保証ではない" in md

    def test_rendering_inserts_blank_line_before_tables_after_bullets(self):
        result = CheckResult(
            run_id="run-spacing",
            current_runs=2,
            baseline_runs=0,
            overall_rate=50.0,
            s1_rate=100.0,
            s1_passed=1,
            s1_total=1,
            thresholds=[ThresholdResult("Overall", 80.0, 50.0, False, "1/2")],
            fresh_case_review_rate=50.0,
            fresh_case_count=1,
            fresh_case_total=2,
            stale_after_days=30,
            stale_cases=[
                CaseStalenessItem(
                    case_id="VPOC001",
                    name="Escalation path",
                    severity="S1",
                    owner="vendor-qa",
                    reference_field="last_reviewed_at",
                    reference_value="2026-03-01",
                    age_days=56,
                    issue="older than 30 days",
                )
            ],
        )

        md = render_gate_markdown(result)

        assert "- Aggregation Policy: latest_run\n\n### Gate Policy / 顧客向け判定ルール" in md
        assert "全回答の完全保証ではない。\n\n| Metric | Actual | Threshold | Status |" in md
        assert "within 30 days\n\n| Case | Severity | Owner | Reference | Age Days | Issue |" in md


# ==================================================================
# Faithfulness gate threshold
# ==================================================================


class TestFaithfulnessGate:
    def test_faithfulness_gate_pass(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        records = [
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,
                faithfulness_score=0.9,
            ),
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA002",
                severity="S2",
                passed=True,
                faithfulness_score=0.8,
            ),
        ]
        (log_dir / f"{today}.jsonl").write_text(
            "\n".join(r.model_dump_json() for r in records) + "\n",
            encoding="utf-8",
        )
        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=0.0, min_faithfulness=70.0)
        result = run_check(str(log_dir), cfg, days=1)
        assert result.gate_passed is True
        faith = [t for t in result.thresholds if t.name == "Avg faithfulness"]
        assert len(faith) == 1
        assert faith[0].actual == pytest.approx(85.0)  # (0.9+0.8)/2 * 100

    def test_faithfulness_gate_fail(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        records = [
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,
                faithfulness_score=0.5,
            ),
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA002",
                severity="S2",
                passed=True,
                faithfulness_score=0.4,
            ),
        ]
        (log_dir / f"{today}.jsonl").write_text(
            "\n".join(r.model_dump_json() for r in records) + "\n",
            encoding="utf-8",
        )
        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=0.0, min_faithfulness=70.0)
        result = run_check(str(log_dir), cfg, days=1)
        assert result.gate_passed is False
        faith = [t for t in result.thresholds if t.name == "Avg faithfulness"]
        assert faith[0].actual == pytest.approx(45.0)

    def test_faithfulness_zero_disables_check(self, log_dir_with_records):
        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=0.0, min_faithfulness=0.0)
        result = run_check(log_dir_with_records, cfg, days=1)
        assert not any(t.name == "Avg faithfulness" for t in result.thresholds)

    def test_no_scored_records_yields_zero(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        records = [
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,  # faithfulness_score=None
            ),
        ]
        (log_dir / f"{today}.jsonl").write_text(
            "\n".join(r.model_dump_json() for r in records) + "\n",
            encoding="utf-8",
        )
        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=0.0, min_faithfulness=50.0)
        result = run_check(str(log_dir), cfg, days=1)
        faith = [t for t in result.thresholds if t.name == "Avg faithfulness"]
        assert len(faith) == 1
        assert faith[0].actual == 0.0
        assert faith[0].passed is False

    def test_from_yaml_reads_min_faithfulness(self, tmp_path):
        yaml_path = tmp_path / "gate.yml"
        yaml_path.write_text(
            "thresholds:\n  min_faithfulness: 75.0\n",
            encoding="utf-8",
        )
        cfg = GateConfig.from_yaml(str(yaml_path))
        assert cfg.min_faithfulness == 75.0


# ==================================================================
# Evidence recall gate threshold
# ==================================================================


class TestEvidenceRecallGate:
    def test_evidence_recall_gate_pass(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        records = [
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,
                evidence_recall=1.0,
            ),
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA002",
                severity="S2",
                passed=True,
                evidence_recall=0.8,
            ),
        ]
        (log_dir / f"{today}.jsonl").write_text(
            "\n".join(r.model_dump_json() for r in records) + "\n",
            encoding="utf-8",
        )
        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=0.0, min_evidence_recall=85.0)
        result = run_check(str(log_dir), cfg, days=1)
        assert result.gate_passed is True
        recall = [t for t in result.thresholds if t.name == "Avg expected evidence recall"]
        assert len(recall) == 1
        assert recall[0].actual == pytest.approx(90.0)

    def test_evidence_recall_gate_fail(self, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y%m%d")
        records = [
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,
                evidence_recall=0.6,
            ),
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA002",
                severity="S2",
                passed=True,
                evidence_recall=0.4,
            ),
        ]
        (log_dir / f"{today}.jsonl").write_text(
            "\n".join(r.model_dump_json() for r in records) + "\n",
            encoding="utf-8",
        )
        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=0.0, min_evidence_recall=70.0)
        result = run_check(str(log_dir), cfg, days=1)
        assert result.gate_passed is False
        recall = [t for t in result.thresholds if t.name == "Avg expected evidence recall"]
        assert recall[0].actual == pytest.approx(50.0)

    def test_evidence_recall_zero_disables_check(self, log_dir_with_records):
        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=0.0, min_evidence_recall=0.0)
        result = run_check(log_dir_with_records, cfg, days=1)
        assert not any(t.name == "Avg expected evidence recall" for t in result.thresholds)

    def test_from_yaml_reads_min_evidence_recall(self, tmp_path):
        yaml_path = tmp_path / "gate.yml"
        yaml_path.write_text(
            "thresholds:\n  min_evidence_recall: 90.0\n",
            encoding="utf-8",
        )
        cfg = GateConfig.from_yaml(str(yaml_path))
        assert cfg.min_evidence_recall == 90.0


# ------------------------------------------------------------------
# Warn status tests
# ------------------------------------------------------------------


class TestWarnStatus:
    """Tests for the warn gate status feature."""

    def _make_log_dir(self, tmp_path, records):
        """Helper: write QARunRecord list into a temp JSONL log dir."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir(exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        jsonl = log_dir / f"{today}.jsonl"
        with open(jsonl, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(rec.model_dump_json() + "\n")
        return str(log_dir)

    def test_gate_config_warn_defaults_to_disabled(self):
        cfg = GateConfig()
        assert cfg.s1_pass_rate_warn == 0.0
        assert cfg.overall_pass_rate_warn == 0.0
        assert cfg.judge_relevance_warn == 0.0

    def test_gate_config_warn_from_yaml(self, tmp_path):
        yaml_path = tmp_path / "gate.yml"
        yaml_path.write_text(
            (
                "thresholds:\n"
                "  s1_pass_rate: 100.0\n"
                "  overall_pass_rate: 80.0\n"
                "  s1_pass_rate_warn: 100.0\n"
                "  overall_pass_rate_warn: 90.0\n"
                "  judge_relevance_warn: 30.0\n"
            ),
            encoding="utf-8",
        )
        cfg = GateConfig.from_yaml(str(yaml_path))
        assert cfg.s1_pass_rate_warn == 100.0
        assert cfg.overall_pass_rate_warn == 90.0
        assert cfg.judge_relevance_warn == 30.0

    def test_gate_status_pass_when_above_warn(self, tmp_path):
        """Metrics above both fail and warn thresholds → pass."""
        records = [
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,
            ),
        ]
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(
            s1_pass_rate=100.0,
            overall_pass_rate=80.0,
            overall_pass_rate_warn=90.0,
        )
        result = run_check(log_dir, cfg, days=1)
        assert result.gate_passed is True
        assert result.gate_status == "pass"

    def test_judge_relevance_warn_triggers(self, tmp_path):
        records = [
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,
                judge_relevance=0.25,
            ),
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="r1",
                case_id="QA002",
                severity="S2",
                passed=True,
                judge_relevance=0.35,
            ),
        ]
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(
            s1_pass_rate=0.0,
            overall_pass_rate=0.0,
            judge_relevance_warn=40.0,
        )

        result = run_check(log_dir, cfg, days=1)

        assert result.gate_passed is True
        assert result.gate_status == "warn"
        judge_check = [t for t in result.thresholds if t.name == "Avg judge relevance"]
        assert len(judge_check) == 1
        assert judge_check[0].warned is True
        assert judge_check[0].actual == pytest.approx(30.0)

    def test_judge_relevance_warn_disabled_when_zero(self, tmp_path):
        records = [
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,
                judge_relevance=0.1,
            ),
        ]
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(s1_pass_rate=0.0, overall_pass_rate=0.0, judge_relevance_warn=0.0)

        result = run_check(log_dir, cfg, days=1)

        assert result.gate_status == "pass"
        assert not any(t.name == "Avg judge relevance" for t in result.thresholds)

    def test_gate_status_warn_when_between_fail_and_warn(self, tmp_path):
        """Metrics above fail but below warn → warn."""
        # 8 pass, 2 fail → 80%. fail=70%, warn=90%
        records = []
        now = datetime.now(timezone.utc)
        for i in range(8):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S2",
                    passed=True,
                )
            )
        for i in range(8, 10):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S2",
                    passed=False,
                    failure_type="keyword_miss",
                    failure_category="synthesis",
                )
            )
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(
            s1_pass_rate=0.0,
            overall_pass_rate=70.0,
            overall_pass_rate_warn=90.0,
        )
        result = run_check(log_dir, cfg, days=1)
        assert result.gate_passed is True  # above fail threshold
        assert result.gate_status == "warn"  # below warn threshold

    def test_gate_status_fail_trumps_warn(self, tmp_path):
        """When fail threshold is missed, status is fail even if warn is set."""
        # 6 pass, 4 fail → 60%. fail=70%, warn=90%
        records = []
        now = datetime.now(timezone.utc)
        for i in range(6):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S2",
                    passed=True,
                )
            )
        for i in range(6, 10):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S2",
                    passed=False,
                    failure_type="keyword_miss",
                    failure_category="synthesis",
                )
            )
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(
            s1_pass_rate=0.0,
            overall_pass_rate=70.0,
            overall_pass_rate_warn=90.0,
        )
        result = run_check(log_dir, cfg, days=1)
        assert result.gate_passed is False
        assert result.gate_status == "fail"

    def test_warn_disabled_when_threshold_zero(self, tmp_path):
        """When warn threshold is 0, never warn."""
        # 8 pass, 2 fail → 80%. fail=70%, warn=0 (disabled)
        records = []
        now = datetime.now(timezone.utc)
        for i in range(8):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S2",
                    passed=True,
                )
            )
        for i in range(8, 10):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S2",
                    passed=False,
                    failure_type="keyword_miss",
                    failure_category="synthesis",
                )
            )
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(
            s1_pass_rate=0.0,
            overall_pass_rate=70.0,
            overall_pass_rate_warn=0.0,  # disabled
        )
        result = run_check(log_dir, cfg, days=1)
        assert result.gate_status == "pass"

    def test_s1_warn_triggers(self, tmp_path):
        """S1 warn threshold triggers when S1 passes fail but misses warn."""
        # 9 S1 pass, 1 S1 fail → 90%. S1 fail=80%, S1 warn=100%
        records = []
        now = datetime.now(timezone.utc)
        for i in range(9):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S1",
                    passed=True,
                )
            )
        records.append(
            QARunRecord(
                timestamp=now,
                run_id="r1",
                case_id="QA009",
                severity="S1",
                passed=False,
                failure_type="keyword_miss",
                failure_category="synthesis",
            )
        )
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(
            s1_pass_rate=80.0,
            overall_pass_rate=80.0,
            s1_pass_rate_warn=100.0,
        )
        result = run_check(log_dir, cfg, days=1)
        assert result.gate_passed is True
        assert result.gate_status == "warn"
        # The S1 threshold should be marked as warned
        s1_check = [t for t in result.thresholds if t.name == "S1 pass rate"][0]
        assert s1_check.passed is True
        assert s1_check.warned is True

    def test_threshold_result_warned_flag(self):
        """ThresholdResult.warned tracks warning state independently."""
        # Passed but warned
        t = ThresholdResult(
            name="test",
            threshold=80.0,
            actual=85.0,
            passed=True,
            warn_threshold=90.0,
            warned=True,
        )
        assert t.passed is True
        assert t.warned is True

        # Passed and not warned
        t2 = ThresholdResult(
            name="test",
            threshold=80.0,
            actual=95.0,
            passed=True,
            warn_threshold=90.0,
            warned=False,
        )
        assert t2.passed is True
        assert t2.warned is False

    def test_build_gate_decision_warn_status(self, tmp_path):
        """build_gate_decision emits 'warn' status with reasons."""
        records = []
        now = datetime.now(timezone.utc)
        for i in range(8):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S2",
                    passed=True,
                )
            )
        for i in range(8, 10):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S2",
                    passed=False,
                    failure_type="keyword_miss",
                    failure_category="synthesis",
                )
            )
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(
            s1_pass_rate=0.0,
            overall_pass_rate=70.0,
            overall_pass_rate_warn=90.0,
        )
        result = run_check(log_dir, cfg, days=1)
        decision = build_gate_decision(result)

        assert decision.status == "warn"
        assert any("WARN" in r for r in decision.reasons)

    def test_build_gate_decision_pass_no_warn_reasons(self, tmp_path):
        """When gate passes cleanly, no warn reasons are emitted."""
        records = [
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,
            ),
        ]
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(
            s1_pass_rate=100.0,
            overall_pass_rate=80.0,
            overall_pass_rate_warn=90.0,
        )
        result = run_check(log_dir, cfg, days=1)
        decision = build_gate_decision(result)

        assert decision.status == "pass"
        assert not any("WARN" in r for r in decision.reasons)

    def test_render_gate_markdown_warn_header(self, tmp_path):
        """Markdown report shows WARN in title and table."""
        records = []
        now = datetime.now(timezone.utc)
        for i in range(8):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S2",
                    passed=True,
                )
            )
        for i in range(8, 10):
            records.append(
                QARunRecord(
                    timestamp=now,
                    run_id="r1",
                    case_id=f"QA{i:03d}",
                    severity="S2",
                    passed=False,
                    failure_type="keyword_miss",
                    failure_category="synthesis",
                )
            )
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(
            s1_pass_rate=0.0,
            overall_pass_rate=70.0,
            overall_pass_rate_warn=90.0,
        )
        result = run_check(log_dir, cfg, days=1)
        md = render_gate_markdown(result)

        assert "## RAG Quality Gate: WARN" in md
        assert "| WARN |" in md

    def test_render_gate_markdown_pass_no_warn_icon(self, tmp_path):
        """When passing cleanly, no WARN icon appears."""
        records = [
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="r1",
                case_id="QA001",
                severity="S1",
                passed=True,
            ),
        ]
        log_dir = self._make_log_dir(tmp_path, records)
        cfg = GateConfig(
            s1_pass_rate=100.0,
            overall_pass_rate=80.0,
        )
        result = run_check(log_dir, cfg, days=1)
        md = render_gate_markdown(result)

        assert "## RAG Quality Gate: PASS" in md
        assert "| WARN |" not in md
