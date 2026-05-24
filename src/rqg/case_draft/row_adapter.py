"""Adapters from internal draft candidates to formal cases.csv rows."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from rqg.case_draft.draft_case import DraftCaseCandidate
from rqg.quality.case_schema import (
    FORMAL_CASE_FIELDS,
    VALID_SEVERITIES,
    infer_eval_mode,
    infer_source_doc,
)

_UNAPPROVED_DRAFT_MARKER = "answer_status:unapproved-draft"


def draft_candidate_to_case_row(candidate: DraftCaseCandidate) -> dict[str, str]:
    """Convert a DraftCaseCandidate to a formal cases.csv-compatible row."""
    _validate_candidate(candidate)
    severity = _validate_review_artifact_severity(candidate.severity)
    notes = _merge_notes(candidate.notes, _UNAPPROVED_DRAFT_MARKER)
    expected_evidence = _normalize_expected_evidence(candidate.expected_evidence)
    row = {
        "case_id": candidate.case_id,
        "name": candidate.case_id,
        "status": "needs_review",
        "severity": severity,
        "eval_mode": infer_eval_mode(
            expected_answer=candidate.expected_answer,
            expected_evidence=expected_evidence,
            expected_keywords="",
        ),
        "question": candidate.question.strip(),
        "expected_answer": candidate.expected_answer.strip(),
        "expected_evidence": expected_evidence,
        "expected_keywords": "",
        "category": candidate.category.strip() or "general",
        "source_doc": _infer_source_doc_from_any_evidence(expected_evidence),
        "owner": "",
        "min_case_score": "100" if severity == "S1" else "85",
        "updated_at": _today_utc(),
        "last_reviewed_at": "",
        "notes": notes,
    }
    return {field: row.get(field, "") for field in FORMAL_CASE_FIELDS}


def draft_candidates_to_case_rows(
    candidates: Sequence[DraftCaseCandidate],
) -> list[dict[str, str]]:
    """Convert multiple draft candidates to formal cases.csv-compatible rows."""
    return [draft_candidate_to_case_row(candidate) for candidate in candidates]


def _validate_candidate(candidate: DraftCaseCandidate) -> None:
    if candidate.status != "needs_review":
        raise ValueError("Draft candidate row adapter only accepts status=needs_review")
    if candidate.status == "active":
        raise ValueError("Draft candidate row adapter must not output active cases")
    if not candidate.question.strip():
        raise ValueError("Draft candidate question must not be empty")
    if not candidate.expected_answer.strip():
        raise ValueError("Draft candidate expected_answer must not be empty")


def _validate_review_artifact_severity(severity: str) -> str:
    normalized = str(severity or "").strip().upper()
    if not normalized:
        raise ValueError("Draft review artifact severity must not be empty")
    if normalized not in VALID_SEVERITIES:
        allowed = ", ".join(sorted(VALID_SEVERITIES))
        raise ValueError(
            f"Draft review artifact severity must be one of {allowed}; got {severity!r}"
        )
    return normalized


def _merge_notes(*notes: str) -> str:
    parts: list[str] = []
    for raw_note in notes:
        for part in raw_note.split(";"):
            marker = part.strip()
            if marker and marker not in parts:
                parts.append(marker)
    return "; ".join(parts)


def _normalize_expected_evidence(expected_evidence: str) -> str:
    parts: list[str] = []
    for raw_part in expected_evidence.replace(",", ";").split(";"):
        part = raw_part.strip()
        if part and part not in parts:
            parts.append(part)
    return ";".join(parts)


def _infer_source_doc_from_any_evidence(expected_evidence: str) -> str:
    for part in expected_evidence.split(";"):
        token = part.strip()
        if "/" in token or "\\" in token:
            return token.split("#", 1)[0]
    return infer_source_doc(expected_evidence=expected_evidence)


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
