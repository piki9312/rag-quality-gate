from __future__ import annotations

from pathlib import Path

from rqg.case_assets import load_case_intent_registry
from rqg.case_draft import (
    PatternDraftPipeline,
    SourceSection,
    create_pattern_draft_case_rows,
)
from rqg.quality.case_schema import FORMAL_CASE_FIELDS


def _registry():
    return load_case_intent_registry(Path("assets/case_intents"))


def test_creates_rows_from_affected_categories() -> None:
    rows = PatternDraftPipeline(_registry()).create_case_rows_for_affected_categories(["refund"])

    assert len(rows) >= 1
    assert rows[0]["status"] == "needs_review"
    assert rows[0]["category"] == "refund"
    assert "intent:refund_mid_contract_cancellation" in rows[0]["notes"]
    assert "generated_by:case_draft_engine" in rows[0]["notes"]
    assert "answer_status:unapproved-draft" in rows[0]["notes"]


def test_empty_categories_returns_empty_list() -> None:
    assert PatternDraftPipeline(_registry()).create_case_rows_for_affected_categories([]) == []


def test_unknown_category_returns_empty_list() -> None:
    rows = PatternDraftPipeline(_registry()).create_case_rows_for_affected_categories(["pricing"])

    assert rows == []


def test_source_sections_are_used() -> None:
    section = SourceSection(
        section_id="refund_policy_v2",
        text="refund_policy details",
        source_ref="docs/refund_policy.md#sec-1",
    )

    rows = create_pattern_draft_case_rows(_registry(), ["refund"], [section])

    assert len(rows) == 1
    assert "source:refund_policy_v2" in rows[0]["notes"]
    assert rows[0]["source_doc"] == "docs/refund_policy.md"
    assert "docs/refund_policy.md#sec-1" in rows[0]["expected_evidence"]


def test_no_active_rows() -> None:
    rows = PatternDraftPipeline(_registry()).create_case_rows_for_affected_categories(["refund"])

    assert rows
    assert all(row["status"] != "active" for row in rows)


def test_rows_are_formal_schema_compatible() -> None:
    rows = PatternDraftPipeline(_registry()).create_case_rows_for_affected_categories(["refund"])

    assert rows
    assert all(list(row.keys()) == FORMAL_CASE_FIELDS for row in rows)


def test_duplicate_affected_categories_do_not_duplicate_rows() -> None:
    rows = PatternDraftPipeline(_registry()).create_case_rows_for_affected_categories(
        ["refund", "contract_terms"]
    )

    assert [row["case_id"] for row in rows] == ["DRAFT-refund_mid_contract_cancellation"]


def test_integration_with_sample_intent() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    rows = create_pattern_draft_case_rows(registry, ["refund"])

    assert len(rows) == 1
    assert rows[0]["case_id"] == "DRAFT-refund_mid_contract_cancellation"
