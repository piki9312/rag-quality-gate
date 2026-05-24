from __future__ import annotations

from pathlib import Path

import pytest

from rqg.case_assets import load_case_intent_registry
from rqg.case_draft import (
    CaseDraftPlanner,
    DraftCaseCandidate,
    SourceSection,
    draft_candidate_to_case_row,
    draft_candidates_to_case_rows,
)
from rqg.quality.case_schema import FORMAL_CASE_FIELDS, validate_case_row


def _candidate(status: str = "needs_review", severity: str = "S1") -> DraftCaseCandidate:
    return DraftCaseCandidate(
        case_id="DRAFT-refund_mid_contract_cancellation",
        status=status,
        severity=severity,
        category="refund",
        question="契約途中で解約した場合、返金されますか？",
        expected_answer="最新の返金・契約条件に基づき案内する。",
        expected_evidence="refund_policy, docs/refund_policy.md#sec-1",
        notes=(
            "generated_by:case_draft_engine; "
            "case_type:generated-draft; "
            "intent:refund_mid_contract_cancellation; "
            "pattern:refund_rule_reversal; "
            "source:refund-policy#sec-1"
        ),
    )


def test_converts_draft_candidate_to_row() -> None:
    row = draft_candidate_to_case_row(_candidate())

    assert row["case_id"] == "DRAFT-refund_mid_contract_cancellation"
    assert row["status"] == "needs_review"
    assert row["severity"] == "S1"
    assert row["category"] == "refund"
    assert row["question"]
    assert row["expected_answer"]
    assert row["expected_evidence"]
    assert row["notes"]


def test_status_remains_needs_review() -> None:
    row = draft_candidate_to_case_row(_candidate())

    assert row["status"] == "needs_review"


def test_does_not_allow_active_candidate() -> None:
    with pytest.raises(ValueError, match="status=needs_review"):
        draft_candidate_to_case_row(_candidate(status="active"))


@pytest.mark.parametrize("severity", ["S3", "S4", "", "unknown"])
def test_rejects_unsupported_severity(severity: str) -> None:
    with pytest.raises(ValueError, match="severity"):
        draft_candidate_to_case_row(_candidate(severity=severity))


def test_preserves_notes_markers() -> None:
    row = draft_candidate_to_case_row(_candidate())

    assert "generated_by:case_draft_engine" in row["notes"]
    assert "case_type:generated-draft" in row["notes"]
    assert "intent:refund_mid_contract_cancellation" in row["notes"]
    assert "pattern:refund_rule_reversal" in row["notes"]


def test_marks_answer_as_unapproved_draft() -> None:
    row = draft_candidate_to_case_row(_candidate())

    assert "answer_status:unapproved-draft" in row["notes"]


def test_preserves_source_info() -> None:
    row = draft_candidate_to_case_row(_candidate())

    assert "source:refund-policy#sec-1" in row["notes"]
    assert "docs/refund_policy.md#sec-1" in row["expected_evidence"]
    assert row["source_doc"] == "docs/refund_policy.md"


def test_converts_multiple_candidates() -> None:
    rows = draft_candidates_to_case_rows([_candidate(), _candidate()])

    assert len(rows) == 2
    assert all(row["status"] == "needs_review" for row in rows)


def test_integration_with_planner() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))
    source_section = SourceSection(
        section_id="refund_policy_v2",
        text="refund_policy details",
        source_ref="docs/refund_policy.md#sec-1",
    )
    drafts = CaseDraftPlanner(registry).create_drafts_for_affected_categories_with_sections(
        ["refund"],
        [source_section],
    )

    rows = draft_candidates_to_case_rows(drafts)

    assert len(rows) == 1
    assert rows[0]["status"] == "needs_review"
    assert "source:refund_policy_v2" in rows[0]["notes"]
    assert "answer_status:unapproved-draft" in rows[0]["notes"]


def test_rows_are_cases_csv_compatible() -> None:
    row = draft_candidate_to_case_row(_candidate())

    assert list(row.keys()) == FORMAL_CASE_FIELDS
    errors = validate_case_row(row)
    assert not [error for error in errors if error.level == "error"]
