"""Tests for CSV case loader."""

from __future__ import annotations

import csv
import json

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
            "last_reviewed_at": "2026-03-29",
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
            "last_reviewed_at": "",
        },
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


@pytest.fixture()
def cases_json_eval_case(tmp_path):
    path = tmp_path / "cases.json"
    payload = [
        {
            "case_id": "J001",
            "question": "When should paid leave be requested?",
            "expected_evidence": ["doc/leave-policy#section-1"],
            "expected_keywords": ["paid leave", "5 business days"],
            "risk_level": "S1",
            "doc_snapshot_id": "snapshot-001",
            "notes": "generated from snapshot",
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


@pytest.fixture()
def cases_json_qa_shape(tmp_path):
    path = tmp_path / "qa_cases.json"
    payload = [
        {
            "case_id": "J002",
            "name": "json qa case",
            "question": "How should employees submit paid leave requests?",
            "severity": "s2",
            "expected_chunks": ["chunk-1"],
            "expected_keywords": ["submit", "HR system"],
            "category": "procedure",
            "owner": "hr-team",
            "min_pass_rate": 85,
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")
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

    def test_last_reviewed_at_parsed(self, cases_csv):
        cases = load_cases(cases_csv)
        assert cases[0].last_reviewed_at == "2026-03-29"
        assert cases[1].last_reviewed_at == ""

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_cases("/nonexistent/cases.csv")

    def test_load_json_eval_case_shape(self, cases_json_eval_case):
        cases = load_cases(cases_json_eval_case)
        assert len(cases) == 1
        assert cases[0].case_id == "J001"
        assert cases[0].severity == "S1"
        assert cases[0].name == "J001"
        assert "paid leave" in cases[0].expected_keywords

    def test_load_json_qa_shape(self, cases_json_qa_shape):
        cases = load_cases(cases_json_qa_shape)
        assert len(cases) == 1
        assert cases[0].case_id == "J002"
        assert cases[0].severity == "S2"
        assert cases[0].expected_chunks == ["chunk-1"]

    def test_invalid_json_raises_value_error(self, tmp_path):
        path = tmp_path / "broken.json"
        path.write_text("{invalid", encoding="utf-8")
        with pytest.raises(ValueError):
            load_cases(str(path))
