from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

from rqg.casegen.generator import generate_eval_cases_from_snapshot
from rqg.domain import DocumentSnapshot


def _tmp_doc(suffix: str) -> Path:
    tmp_dir = Path("tests/.tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir / f"{uuid.uuid4()}-{suffix}.md"


def test_generate_eval_cases_from_snapshot_rule_mode():
    doc = _tmp_doc("generator")
    doc.write_text(
        "# Leave Policy\n\nPaid leave requests must be submitted 5 business days in advance.",
        encoding="utf-8",
    )
    snapshot = DocumentSnapshot(
        snapshot_id="snapshot-001",
        doc_id="docs/leave_policy.md",
        title="Leave Policy",
        source_path=doc.as_posix(),
        content_hash="hash",
        created_at="2026-03-23T00:00:00Z",
    )

    bundle = generate_eval_cases_from_snapshot(snapshot, mode="rule", max_cases=10, use_llm=False)

    assert len(bundle.sections) == 1
    assert len(bundle.cases) == 1
    assert bundle.cases[0].expected_evidence[0].endswith("#sec-1")
    assert bundle.cases[0].doc_snapshot_id == "snapshot-001"
    assert bundle.cases[0].question == "When should paid leave requests be submitted?"
    assert bundle.cases[0].category == "deadline"


def test_generate_eval_cases_hybrid_uses_rule_when_llm_fails():
    doc = _tmp_doc("generator2")
    doc.write_text(
        "# Leave Policy\n\nPaid leave requests must be submitted 5 business days in advance.",
        encoding="utf-8",
    )
    snapshot = DocumentSnapshot(
        snapshot_id="snapshot-001",
        doc_id="docs/leave_policy.md",
        title="Leave Policy",
        source_path=doc.as_posix(),
        content_hash="hash",
        created_at="2026-03-23T00:00:00Z",
    )

    with patch("rqg.casegen.generator.generate_llm_questions", side_effect=RuntimeError("boom")):
        bundle = generate_eval_cases_from_snapshot(
            snapshot, mode="hybrid", max_cases=10, use_llm=True
        )

    assert len(bundle.cases) == 1


def test_generate_eval_cases_dedupes_semantic_duplicate_questions():
    doc = _tmp_doc("generator3")
    doc.write_text(
        "# Leave Policy\n\nPaid leave requests must be submitted 5 business days in advance.",
        encoding="utf-8",
    )
    snapshot = DocumentSnapshot(
        snapshot_id="snapshot-001",
        doc_id="docs/leave_policy.md",
        title="Leave Policy",
        source_path=doc.as_posix(),
        content_hash="hash",
        created_at="2026-03-23T00:00:00Z",
    )

    with (
        patch(
            "rqg.casegen.generator.generate_rule_questions",
            return_value=["有給申請期限はいつまでですか？"],
        ),
        patch(
            "rqg.casegen.generator.generate_llm_questions",
            return_value=["有給申請期限はいつまでですか？  "],
        ),
    ):
        bundle = generate_eval_cases_from_snapshot(
            snapshot, mode="hybrid", max_cases=10, use_llm=True
        )

    assert len(bundle.cases) == 1


def test_generate_eval_cases_skips_low_information_section():
    doc = _tmp_doc("generator4")
    doc.write_text("# Leave Policy\n\n短文", encoding="utf-8")
    snapshot = DocumentSnapshot(
        snapshot_id="snapshot-001",
        doc_id="docs/leave_policy.md",
        title="Leave Policy",
        source_path=doc.as_posix(),
        content_hash="hash",
        created_at="2026-03-23T00:00:00Z",
    )

    bundle = generate_eval_cases_from_snapshot(snapshot, mode="rule", max_cases=10, use_llm=False)

    assert bundle.cases == []


def test_generate_eval_cases_marks_mixed_question_notes():
    doc = _tmp_doc("generator5")
    doc.write_text(
        "## 1. 締め日と提出方法\n\n経費精算の締め日は毎月25日です。\n25日までにレシート原本を添付の上、経費精算システムから申請してください。",
        encoding="utf-8",
    )
    snapshot = DocumentSnapshot(
        snapshot_id="snapshot-001",
        doc_id="packs/hr/documents/経費精算ガイドライン.md",
        title="経費精算ガイドライン",
        source_path=doc.as_posix(),
        content_hash="hash",
        created_at="2026-03-23T00:00:00Z",
    )

    with patch(
        "rqg.casegen.generator.generate_rule_questions",
        return_value=["1. 締め日と提出方法はいつまでに対応する必要がありますか？"],
    ):
        bundle = generate_eval_cases_from_snapshot(
            snapshot, mode="rule", max_cases=10, use_llm=False
        )

    assert len(bundle.cases) == 3
    assert bundle.cases[0].notes is not None
    assert bundle.cases[0].question == "締め日と提出方法はいつまでに対応する必要がありますか？"
    assert bundle.cases[0].category == "general"
    assert "mixed_question:deadline,procedure" in bundle.cases[0].notes
    assert "manual_review_priority:high" in bundle.cases[0].notes
    split_questions = {case.question for case in bundle.cases[1:]}
    assert "締め日はいつですか？" in split_questions
    assert "経費精算の提出方法は何ですか？" in split_questions
    by_question = {case.question: case for case in bundle.cases[1:]}
    assert by_question["締め日はいつですか？"].category == "deadline"
    assert by_question["経費精算の提出方法は何ですか？"].category == "procedure"
    assert all(case.notes is not None for case in bundle.cases[1:])
    assert all("split_candidate_from:" in (case.notes or "") for case in bundle.cases[1:])


def test_generate_eval_cases_from_english_snapshot_emits_multiple_questions():
    doc = _tmp_doc("generator6")
    doc.write_text(
        "# Access FAQ\n\nTemporary VPN exception access must be requested at least 2 business days before access is needed.\n\nRequest method:\n\n- Submit through the IT service portal\n- Include business reason, requested dates, and manager approval\n",
        encoding="utf-8",
    )
    snapshot = DocumentSnapshot(
        snapshot_id="snapshot-english-001",
        doc_id="packs/wiki/documents/access_faq.md",
        title="access_faq",
        source_path=doc.as_posix(),
        content_hash="hash",
        created_at="2026-03-23T00:00:00Z",
    )

    bundle = generate_eval_cases_from_snapshot(snapshot, mode="rule", max_cases=10, use_llm=False)

    questions = {case.question: case.category for case in bundle.cases}
    assert questions == {
        "When should temporary VPN exception access be requested?": "deadline",
        "How should employees submit a temporary VPN exception request?": "procedure",
    }
