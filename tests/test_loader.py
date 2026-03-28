"""Tests for CSV case loader."""

from __future__ import annotations

import csv

import pytest

from rqg.quality.loader import load_cases


@pytest.fixture()
def cases_csv(tmp_path):
    """Create a minimal cases CSV."""
    path = tmp_path / "cases.csv"
    rows = [
        {
            "case_id": "T001",
            "name": "有給",
            "severity": "S1",
            "question": "有給の期限は？",
            "expected_chunks": "chunk_A;chunk_B",
            "expected_keywords": "5営業日;申請",
            "golden_answer": "",
            "category": "就業規則",
            "owner": "hr-team",
            "min_pass_rate": "100",
        },
        {
            "case_id": "T002",
            "name": "経費",
            "severity": "s2",
            "question": "締め日は？",
            "expected_chunks": "",
            "expected_keywords": "25日",
            "golden_answer": "",
            "category": "経費",
            "owner": "",
            "min_pass_rate": "",
        },
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


class TestLoadCases:
    def test_load_count(self, cases_csv):
        cases = load_cases(cases_csv)
        assert len(cases) == 2

    def test_severity_upper(self, cases_csv):
        cases = load_cases(cases_csv)
        assert cases[0].severity == "S1"
        assert cases[1].severity == "S2"  # lower → upper

    def test_semicolon_split(self, cases_csv):
        cases = load_cases(cases_csv)
        assert cases[0].expected_chunks == ["chunk_A", "chunk_B"]
        assert cases[0].expected_keywords == ["5営業日", "申請"]

    def test_empty_list(self, cases_csv):
        cases = load_cases(cases_csv)
        assert cases[1].expected_chunks == []

    def test_min_pass_rate_parsed(self, cases_csv):
        cases = load_cases(cases_csv)
        assert cases[0].min_pass_rate == 100.0
        assert cases[1].min_pass_rate == 0.0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_cases("/nonexistent/cases.csv")
