"""Tests for models — QATestCase, EvalResult, EvalRun, QARunRecord."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from rqg.quality.models import EvalResult, EvalRun, QARunRecord, QATestCase


class TestEvalRun:
    def test_post_init_counts(self, passed_result, failed_result):
        run = EvalRun(
            run_id="test-run",
            timestamp=datetime.now(timezone.utc),
            results=[passed_result, failed_result],
        )
        assert run.total == 2
        assert run.passed == 1
        assert run.failed == 1
        assert run.pass_rate == 50.0

    def test_empty_run(self):
        run = EvalRun(run_id="empty", timestamp=datetime.now(timezone.utc), results=[])
        assert run.total == 0
        assert run.pass_rate == 0.0


class TestQARunRecord:
    def test_from_eval_result(self, passed_result, s1_case):
        record = QARunRecord.from_eval_result(passed_result, "run-001", s1_case)
        assert record.case_id == "QA001"
        assert record.severity == "S1"
        assert record.passed is True
        assert record.category == "就業規則"

    def test_round_trip_json(self, passed_result, s1_case):
        record = QARunRecord.from_eval_result(passed_result, "run-001", s1_case)
        json_str = record.model_dump_json()
        restored = QARunRecord.model_validate_json(json_str)
        assert restored.case_id == record.case_id
        assert restored.passed == record.passed

    def test_failure_reasons(self, failed_result, s2_case):
        failed_result.failure_category = "synthesis"
        record = QARunRecord.from_eval_result(failed_result, "run-002", s2_case)
        assert record.failure_type == "keyword_miss"
        assert record.failure_category == "synthesis"
        assert len(record.reasons) == 1

    def test_no_cost_when_zero(self, passed_result, s1_case):
        passed_result.cost_usd = 0.0
        record = QARunRecord.from_eval_result(passed_result, "run-001", s1_case)
        assert record.cost_usd is None
