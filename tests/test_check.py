"""Tests for gate check (check.py)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from rqg.quality.check import (
    CheckResult,
    GateConfig,
    ThresholdResult,
    build_gate_decision,
    load_failure_actions_from_quality_pack,
    load_records,
    render_gate_markdown,
    run_check,
)
from rqg.quality.models import QARunRecord

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


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


class TestGateConfig:
    def test_defaults(self):
        cfg = GateConfig()
        assert cfg.s1_pass_rate == 100.0
        assert cfg.overall_pass_rate == 80.0

    def test_from_yaml(self, tmp_path):
        yaml_path = tmp_path / "gate.yml"
        yaml_path.write_text(
            (
                "thresholds:\n"
                "  s1_pass_rate: 95.0\n"
                "  overall_pass_rate: 75.0\n"
                "  max_overall_drop_pct: 10.0\n"
                "  max_s1_drop_pct: 5.0\n"
            ),
            encoding="utf-8",
        )
        cfg = GateConfig.from_yaml(str(yaml_path))
        assert cfg.s1_pass_rate == 95.0
        assert cfg.overall_pass_rate == 75.0
        assert cfg.max_overall_drop_pct == 10.0
        assert cfg.max_s1_drop_pct == 5.0

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

    def test_no_data_fails(self, tmp_path, gate_config):
        result = run_check(str(tmp_path / "empty"), gate_config, days=1)
        assert result.current_runs == 0
        assert result.gate_passed is False

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
            t.name == "Overall pass rate drop" and t.passed is False
            for t in result.thresholds
        )
        assert any(
            t.name == "S1 pass rate drop" and t.passed is False
            for t in result.thresholds
        )

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
        md = render_gate_markdown(result)
        assert "FAIL" in md
        assert "Failure Categories" in md
        assert "retrieval_miss" in md

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
        )

        md = render_gate_markdown(
            result,
            failure_actions={"retrieval_miss": "Review retrieval settings"},
        )

        assert "Next Actions" in md
        assert "Review retrieval settings" in md
        assert "Define next action in weekly review issue" in md
        assert "T.B.D." in md
