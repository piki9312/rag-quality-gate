"""Validation helpers for draft case candidates."""

from __future__ import annotations

from rqg.case_draft.draft_case import DraftCaseCandidate


def validate_draft_case_candidate(candidate: DraftCaseCandidate) -> DraftCaseCandidate:
    """Validate the minimal safety contract for generated draft candidates."""
    if candidate.status != "needs_review":
        raise ValueError("Draft case candidate status must be needs_review")
    if not candidate.question.strip():
        raise ValueError("Draft case candidate question must not be empty")
    if not candidate.expected_answer.strip():
        raise ValueError("Draft case candidate expected_answer must not be empty")
    required_markers = (
        "generated_by:case_draft_engine",
        "case_type:generated-draft",
        "intent:",
    )
    for marker in required_markers:
        if marker not in candidate.notes:
            raise ValueError(f"Draft case candidate notes missing marker: {marker}")
    if candidate.status == "active":
        raise ValueError("Draft case candidate must not be active")
    return candidate
