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
