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

    assert "# Eval Case Review" in markdown
    assert "## Case: doc_001" in markdown
    assert "- Expected Evidence:" in markdown
    assert "- Expected Keywords:" in markdown
    assert "- Risk Level: S2" in markdown
    assert "- Document Snapshot: snapshot-001" in markdown


def test_render_cases_markdown_handles_empty_expected_keywords():
    case = EvalCase(
        case_id="doc_002",
        question="申請方法は何ですか？",
        expected_evidence=["docs/hr.md#sec-2"],
        expected_keywords=[],
        risk_level="S2",
        doc_snapshot_id="snapshot-002",
        notes="auto-generated",
    )

    markdown = render_cases_markdown([case])
    assert "- Expected Keywords:" in markdown
    assert "  - (none)" in markdown


def test_render_cases_markdown_handles_none_notes():
    case = EvalCase(
        case_id="doc_003",
        question="対象者は誰ですか？",
        expected_evidence=["docs/hr.md#sec-3"],
        expected_keywords=["対象"],
        risk_level="S2",
        doc_snapshot_id="snapshot-003",
        notes=None,
    )

    markdown = render_cases_markdown([case])
    assert "- Notes: (none)" in markdown


def test_write_review_output_markdown_file():
    output = Path("tests/.tmp") / f"{uuid.uuid4()}-review.md"
    write_review_output(output, [_sample_case()])
    content = output.read_text(encoding="utf-8")
    assert "# Eval Case Review" in content
    assert "## Case: doc_001" in content
