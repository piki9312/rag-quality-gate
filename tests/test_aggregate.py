"""Tests for aggregate utilities."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from rqg.quality.aggregate import (
    case_pass_rates,
    failure_breakdown,
    failure_category_breakdown,
    percentile,
    severity_pass_rate,
)


@dataclass
class _FakeResult:
    case_id: str
    severity: str
    passed: bool
    failure_type: str | None = None
    failure_category: str | None = None


class TestSeverityPassRate:
    def test_all_pass(self):
        results = [
            _FakeResult("QA001", "S1", True),
            _FakeResult("QA002", "S1", True),
        ]
        rate, p, t = severity_pass_rate(results, "S1")
        assert rate == 100.0
        assert p == 2
        assert t == 2

    def test_mixed(self):
        results = [
            _FakeResult("QA001", "S1", True),
            _FakeResult("QA002", "S1", False),
        ]
        rate, p, t = severity_pass_rate(results, "S1")
        assert rate == 50.0

    def test_filter_severity(self):
        results = [
            _FakeResult("QA001", "S1", True),
            _FakeResult("QA002", "S2", False),
        ]
        rate, p, t = severity_pass_rate(results, "S1")
        assert t == 1 and p == 1

    def test_empty(self):
        rate, p, t = severity_pass_rate([], "S1")
        assert rate == 0.0 and t == 0


class TestCasePassRates:
    def test_rates(self):
        results = [
            _FakeResult("QA001", "S1", True),
            _FakeResult("QA001", "S1", False),
            _FakeResult("QA002", "S2", True),
        ]
        rates = case_pass_rates(results)
        assert rates["QA001"] == 0.5
        assert rates["QA002"] == 1.0


class TestPercentile:
    def test_p50(self):
        assert percentile([10, 20, 30, 40, 50], 50) == 30

    def test_p95(self):
        assert percentile([10, 20, 30, 40, 50, 60, 70, 80, 90, 100], 95) == 100

    def test_empty(self):
        assert percentile([], 50) == 0.0


class TestFailureBreakdown:
    def test_breakdown(self):
        results = [
            _FakeResult("QA001", "S1", False, "keyword_miss"),
            _FakeResult("QA002", "S1", False, "keyword_miss"),
            _FakeResult("QA003", "S2", False, "retrieval_miss"),
            _FakeResult("QA004", "S2", True, None),
        ]
        bd = failure_breakdown(results)
        assert bd["keyword_miss"] == 2
        assert bd["retrieval_miss"] == 1
        assert "unknown" not in bd

    def test_all_pass(self):
        results = [_FakeResult("QA001", "S1", True)]
        assert failure_breakdown(results) == {}


class TestFailureCategoryBreakdown:
    def test_breakdown(self):
        results = [
            _FakeResult("QA001", "S1", False, "keyword_miss", "synthesis"),
            _FakeResult("QA002", "S1", False, "keyword_miss", "synthesis"),
            _FakeResult("QA003", "S2", False, "error", "tool_failure"),
            _FakeResult("QA004", "S2", True, None, None),
        ]
        bd = failure_category_breakdown(results)
        assert bd["synthesis"] == 2
        assert bd["tool_failure"] == 1

    def test_unknown_when_missing_category(self):
        results = [_FakeResult("QA001", "S1", False, "keyword_miss", None)]
        bd = failure_category_breakdown(results)
        assert bd["unknown"] == 1
