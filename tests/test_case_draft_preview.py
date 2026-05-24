from __future__ import annotations

import csv
import shutil
import uuid
from pathlib import Path

from rqg.case_assets import load_case_intent_registry
from rqg.case_draft import SourceSection, write_pattern_draft_preview_csv
from rqg.quality.case_merge import merge_cases_rows
from rqg.quality.case_schema import FORMAL_CASE_FIELDS


def _workspace_tmp() -> Path:
    root = Path("tests/.tmp") / f"case-draft-preview-{uuid.uuid4()}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _registry():
    return load_case_intent_registry(Path("assets/case_intents"))


def _source_section() -> SourceSection:
    return SourceSection(
        section_id="refund_policy_v2",
        text="refund_policy details",
        source_ref="docs/refund_policy.md#sec-1",
    )


def test_writes_preview_csv_artifact() -> None:
    root = _workspace_tmp()
    try:
        output_path = root / "preview" / "draft-cases.csv"

        result = write_pattern_draft_preview_csv(
            _registry(),
            ["refund"],
            [_source_section()],
            output_path,
        )

        csv_text = output_path.read_text(encoding="utf-8")
        assert output_path.exists()
        assert result.row_count >= 1
        assert "needs_review" in csv_text
        assert "answer_status:unapproved-draft" in csv_text
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_returns_artifact_metadata() -> None:
    root = _workspace_tmp()
    try:
        output_path = root / "draft-cases.csv"

        result = write_pattern_draft_preview_csv(
            _registry(),
            ["refund"],
            [_source_section()],
            output_path,
        )

        assert result.path == output_path
        assert result.rows
        assert result.row_count == len(result.rows)
        assert result.affected_categories == ("refund",)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_zero_rows_writes_header_only() -> None:
    root = _workspace_tmp()
    try:
        output_path = root / "empty-draft-cases.csv"

        result = write_pattern_draft_preview_csv(
            _registry(),
            ["unknown_category"],
            [_source_section()],
            output_path,
        )

        with output_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))

        assert result.row_count == 0
        assert result.rows == []
        assert rows == [FORMAL_CASE_FIELDS]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_active_rows_are_not_written() -> None:
    root = _workspace_tmp()
    try:
        output_path = root / "draft-cases.csv"

        result = write_pattern_draft_preview_csv(
            _registry(),
            ["refund"],
            [_source_section()],
            output_path,
        )

        assert result.rows
        assert all(row["status"] == "needs_review" for row in result.rows)
        assert all(row["status"] != "active" for row in result.rows)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_source_section_is_preserved() -> None:
    root = _workspace_tmp()
    try:
        output_path = root / "draft-cases.csv"

        write_pattern_draft_preview_csv(
            _registry(),
            ["refund"],
            [_source_section()],
            output_path,
        )

        csv_text = output_path.read_text(encoding="utf-8")
        assert "source:refund_policy_v2" in csv_text
        assert "docs/refund_policy.md#sec-1" in csv_text
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_integration_with_sample_intent() -> None:
    root = _workspace_tmp()
    try:
        output_path = root / "draft-cases.csv"

        result = write_pattern_draft_preview_csv(
            load_case_intent_registry(Path("assets/case_intents")),
            ["refund"],
            [],
            output_path,
        )

        assert result.row_count == 1
        assert result.rows[0]["case_id"] == "DRAFT-refund_mid_contract_cancellation"
        assert output_path.exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_preview_artifact_rows_can_enter_existing_review_merge_flow() -> None:
    root = _workspace_tmp()
    try:
        output_path = root / "pattern-draft-review.csv"

        result = write_pattern_draft_preview_csv(
            _registry(),
            ["refund"],
            [_source_section()],
            output_path,
        )

        merged_rows, summary = merge_cases_rows(base_rows=[], review_rows=result.rows)

        assert summary.review_cases == result.row_count == 1
        assert summary.added_case_ids == ["DRAFT-refund_mid_contract_cancellation"]
        assert merged_rows[0]["status"] == "needs_review"
        assert "answer_status:unapproved-draft" in merged_rows[0]["notes"]
    finally:
        shutil.rmtree(root, ignore_errors=True)
