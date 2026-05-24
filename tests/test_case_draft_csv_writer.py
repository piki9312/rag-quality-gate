from __future__ import annotations

import csv
import shutil
import uuid
from pathlib import Path

import pytest

from rqg.case_assets import load_case_intent_registry
from rqg.case_draft import (
    PatternDraftPipeline,
    SourceSection,
    draft_case_rows_to_csv_text,
    write_draft_case_rows_csv,
)
from rqg.quality.case_schema import FORMAL_CASE_FIELDS


def _workspace_tmp() -> Path:
    root = Path("tests/.tmp") / f"case-draft-csv-writer-{uuid.uuid4()}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _rows() -> list[dict[str, str]]:
    registry = load_case_intent_registry(Path("assets/case_intents"))
    section = SourceSection(
        section_id="refund_policy_v2",
        text="refund_policy details",
        source_ref="docs/refund_policy.md#sec-1",
    )
    return PatternDraftPipeline(registry).create_case_rows_for_affected_categories(
        ["refund"],
        [section],
    )


def test_converts_rows_to_csv_text() -> None:
    csv_text = draft_case_rows_to_csv_text(_rows())

    assert csv_text.startswith(",".join(FORMAL_CASE_FIELDS))
    assert "DRAFT-refund_mid_contract_cancellation" in csv_text
    assert "needs_review" in csv_text
    assert "answer_status:unapproved-draft" in csv_text


def test_writes_csv_file() -> None:
    root = _workspace_tmp()
    try:
        output_path = root / "draft-cases.csv"

        write_draft_case_rows_csv(_rows(), output_path)

        assert output_path.exists()
        assert "DRAFT-refund_mid_contract_cancellation" in output_path.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_uses_formal_field_order() -> None:
    root = _workspace_tmp()
    try:
        output_path = root / "draft-cases.csv"
        write_draft_case_rows_csv(_rows(), output_path)

        with output_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)

        assert header == FORMAL_CASE_FIELDS
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_rejects_active_row() -> None:
    row = dict(_rows()[0])
    row["status"] = "active"

    with pytest.raises(ValueError, match="refuses active rows"):
        draft_case_rows_to_csv_text([row])


def test_rejects_non_needs_review_row() -> None:
    row = dict(_rows()[0])
    row["status"] = "draft"

    with pytest.raises(ValueError, match="status=needs_review"):
        draft_case_rows_to_csv_text([row])


@pytest.mark.parametrize("severity", ["S3", "S4", "", "unknown"])
def test_rejects_unsupported_severity(severity: str) -> None:
    row = dict(_rows()[0])
    row["severity"] = severity

    with pytest.raises(ValueError, match="severity"):
        draft_case_rows_to_csv_text([row])


def test_rejects_missing_severity() -> None:
    row = dict(_rows()[0])
    row.pop("severity")

    with pytest.raises(ValueError, match="severity"):
        draft_case_rows_to_csv_text([row])


def test_rejects_empty_question() -> None:
    row = dict(_rows()[0])
    row["question"] = ""

    with pytest.raises(ValueError, match="question"):
        draft_case_rows_to_csv_text([row])


def test_rejects_empty_expected_answer() -> None:
    row = dict(_rows()[0])
    row["expected_answer"] = ""

    with pytest.raises(ValueError, match="expected_answer"):
        draft_case_rows_to_csv_text([row])


def test_preserves_notes_markers() -> None:
    csv_text = draft_case_rows_to_csv_text(_rows())

    assert "generated_by:case_draft_engine" in csv_text
    assert "case_type:generated-draft" in csv_text
    assert "answer_status:unapproved-draft" in csv_text


def test_integration_with_pattern_draft_pipeline() -> None:
    rows = _rows()

    csv_text = draft_case_rows_to_csv_text(rows)

    assert "source:refund_policy_v2" in csv_text
    assert "docs/refund_policy.md#sec-1" in csv_text
