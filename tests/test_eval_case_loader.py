from __future__ import annotations

import csv

import pytest
from pydantic import ValidationError

from rqg.quality.loader import (
    eval_case_to_qa_test_case,
    load_eval_cases,
    qa_test_case_to_eval_case,
)
from rqg.quality.models import QATestCase


@pytest.fixture()
def eval_cases_csv(tmp_path):
    path = tmp_path / "eval_cases.csv"
    fieldnames = [
        "case_id",
        "question",
        "risk_level",
        "severity",
        "expected_evidence",
        "expected_chunks",
        "expected_keywords",
        "doc_snapshot_id",
        "notes",
    ]
    rows = [
        {
            "case_id": "EC001",
            "question": "What is the leave policy?",
            "risk_level": "S1",
            "severity": "",
            "expected_evidence": "chunk_A;chunk_B",
            "expected_chunks": "",
            "expected_keywords": "leave;policy",
            "doc_snapshot_id": "snapshot-001",
            "notes": "critical",
        },
        {
            "case_id": "EC002",
            "question": "What is the reimbursement policy?",
            "risk_level": "",
            "severity": "s2",
            "expected_evidence": "",
            "expected_chunks": "chunk_C",
            "expected_keywords": "reimbursement",
            "doc_snapshot_id": "",
            "notes": "",
        },
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def test_load_eval_cases_reads_existing_csv_shape(eval_cases_csv):
    cases = load_eval_cases(eval_cases_csv)

    assert len(cases) == 2
    assert cases[0].risk_level == "S1"
    assert cases[0].expected_evidence == ["chunk_A", "chunk_B"]
    assert cases[1].risk_level == "S2"
    assert cases[1].doc_snapshot_id == "unlinked-snapshot"


def test_load_eval_cases_requires_non_empty_expected_evidence(tmp_path):
    path = tmp_path / "invalid.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case_id",
                "question",
                "risk_level",
                "expected_evidence",
                "doc_snapshot_id",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "EC003",
                "question": "Invalid case",
                "risk_level": "S1",
                "expected_evidence": "",
                "doc_snapshot_id": "snapshot-003",
            }
        )

    with pytest.raises(ValidationError):
        load_eval_cases(str(path))


def test_eval_case_to_qa_test_case_maps_fields():
    from rqg.domain import EvalCase

    eval_case = EvalCase(
        case_id="EC001",
        question="What is the leave policy?",
        expected_evidence=["chunk_A"],
        expected_keywords=["leave"],
        risk_level="S1",
        doc_snapshot_id="snapshot-001",
    )

    qa_case = eval_case_to_qa_test_case(eval_case, name="Leave policy")

    assert qa_case.case_id == "EC001"
    assert qa_case.severity == "S1"
    assert qa_case.expected_chunks == ["chunk_A"]


def test_qa_test_case_to_eval_case_maps_fields():
    qa_case = QATestCase(
        case_id="QA001",
        name="Leave policy",
        question="What is the leave policy?",
        severity="S2",
        expected_keywords=["leave"],
        expected_chunks=["chunk_A"],
    )

    eval_case = qa_test_case_to_eval_case(qa_case, doc_snapshot_id="snapshot-002")

    assert eval_case.case_id == "QA001"
    assert eval_case.risk_level == "S2"
    assert eval_case.expected_evidence == ["chunk_A"]
