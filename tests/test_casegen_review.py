from __future__ import annotations

import csv
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
        category="policy",
        notes="auto-generated from section 1",
    )


def test_render_cases_markdown_contains_review_columns():
    markdown = render_cases_markdown([_sample_case()])

    assert "# Eval Case Review" in markdown
    assert "## Summary" in markdown
    assert "## Case: doc_001" in markdown
    assert "- Expected Evidence:" in markdown
    assert "- Expected Keywords:" in markdown
    assert "- Risk Level: S2" in markdown
    assert "- Document Snapshot: snapshot-001" in markdown


def test_render_cases_markdown_summarizes_mixed_and_manual_review_priority():
    mixed_case = EvalCase(
        case_id="doc_mixed",
        question="締め日と提出方法はいつまでに対応する必要がありますか？",
        expected_evidence=["docs/hr.md#sec-1"],
        expected_keywords=["締め日", "提出方法"],
        risk_level="S1",
        doc_snapshot_id="snapshot-003",
        category="general",
        notes="auto-generated from section 1; mixed_question:deadline,procedure; manual_review_priority:high",
    )
    split_case = EvalCase(
        case_id="doc_split",
        question="締め日はいつまでに対応する必要がありますか？",
        expected_evidence=["docs/hr.md#sec-1"],
        expected_keywords=["締め日"],
        risk_level="S2",
        doc_snapshot_id="snapshot-003",
        category="deadline",
        notes="auto-generated split candidate from section 1; split_candidate_from:締め日と提出方法はいつまでに対応する必要がありますか; manual_review_priority:medium",
    )

    markdown = render_cases_markdown([mixed_case, split_case])

    assert "- Mixed-question cases: 1" in markdown
    assert "- Split-candidate cases: 1" in markdown
    assert "## Manual Review Priority" in markdown
    mixed_index = markdown.index("doc_mixed")
    split_index = markdown.index("doc_split")
    assert mixed_index < split_index


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


def test_write_review_output_csv_file_includes_lightweight_columns():
    output = Path("tests/.tmp") / f"{uuid.uuid4()}-review.csv"
    write_review_output(output, [_sample_case()])

    with open(output, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert reader.fieldnames is not None
    assert "title" in reader.fieldnames
    assert "question" in reader.fieldnames
    assert "eval_mode" in reader.fieldnames
    assert "expected_evidence" in reader.fieldnames
    assert "expected_keywords" in reader.fieldnames
    assert "source_doc" in reader.fieldnames
    assert "severity" in reader.fieldnames
    assert "notes" in reader.fieldnames
    # Lightweight schema should NOT include formal-only fields
    assert "case_id" not in reader.fieldnames
    assert "expected_chunks" not in reader.fieldnames
    assert "min_pass_rate" not in reader.fieldnames

    assert len(rows) == 1
    row = rows[0]
    assert row["title"] == "doc_001"
    assert row["eval_mode"] == "evidence_keyword"
    assert row["severity"] == "S2"
    assert row["expected_evidence"] == "docs/hr.md#sec-1"
    assert row["expected_keywords"] == "年次有給休暇;申請"
    assert row["source_doc"] == "docs/hr.md"
    assert row["category"] == "policy"
    assert row["notes"] == "auto-generated from section 1"


def test_write_review_output_csv_preserves_s1_severity():
    output = Path("tests/.tmp") / f"{uuid.uuid4()}-review-s1.csv"
    s1_case = _sample_case().model_copy(update={"risk_level": "S1"})
    write_review_output(output, [s1_case])

    with open(output, "r", encoding="utf-8", newline="") as f:
        row = next(csv.DictReader(f))

    assert row["severity"] == "S1"


def test_write_review_output_csv_falls_back_to_doc_snapshot_for_source_doc():
    output = Path("tests/.tmp") / f"{uuid.uuid4()}-review-source-doc.csv"
    case = EvalCase(
        case_id="doc_004",
        question="申請方法は何ですか？",
        expected_evidence=["chunk-1"],
        expected_keywords=["申請"],
        risk_level="S2",
        doc_snapshot_id="snapshot-fallback-001",
        notes="auto-generated",
    )

    write_review_output(output, [case])

    with open(output, "r", encoding="utf-8", newline="") as f:
        row = next(csv.DictReader(f))

    assert row["source_doc"] == "snapshot-fallback-001"
