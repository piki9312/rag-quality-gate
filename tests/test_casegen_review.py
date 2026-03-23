from __future__ import annotations

import uuid
from pathlib import Path

from rqg.casegen.review import render_cases_markdown, write_review_output
from rqg.domain import EvalCase


def _sample_case() -> EvalCase:
    return EvalCase(
        case_id="doc_001",
        question="年次有給休暇はいつまでに申請する必要がありますか？",
        expected_evidence=["docs/hr.md#sec-1"],
        expected_keywords=["年次有給休暇", "申請"],
        risk_level="S2",
        doc_snapshot_id="snapshot-001",
        notes="auto-generated from section 1",
    )


def test_render_cases_markdown_contains_review_columns():
    markdown = render_cases_markdown([_sample_case()])

    assert "| case_id | question | expected_evidence | risk_level | notes |" in markdown
    assert "doc_001" in markdown


def test_write_review_output_csv():
    output = Path("tests/.tmp") / f"{uuid.uuid4()}-review.csv"
    write_review_output(output, [_sample_case()])

    content = output.read_text(encoding="utf-8")
    assert "case_id,question,expected_evidence" in content
    assert "doc_001" in content
