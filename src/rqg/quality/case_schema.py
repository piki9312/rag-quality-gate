"""Case schema definitions, mapper/normalizer, and validation.

This module separates review lightweight output from the formal cases.csv
schema and provides a clean mapping layer between them.

Design principles:
- review (lightweight 7 fields) ≠ cases.csv (formal 14 fields)
- normalize / mapper always sits between them
- Ambiguous cases → needs_review (prefer safety over automation)
- Implementation-dependent names (expected_chunks) → evidence-oriented names
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

# ======================================================================
# Constants
# ======================================================================

FORMAL_CASE_FIELDS: list[str] = [
    "case_id",
    "name",
    "status",
    "severity",
    "question",
    "expected_answer",
    "expected_evidence",
    "category",
    "source_doc",
    "owner",
    "min_case_score",
    "updated_at",
    "last_reviewed_at",
    "notes",
]

REVIEW_OUTPUT_FIELDS: list[str] = [
    "title",
    "question",
    "expected_answer",
    "expected_evidence",
    "severity",
    "category",
    "notes",
]

VALID_STATUSES = {"draft", "active", "needs_review", "deprecated"}
VALID_SEVERITIES = {"S1", "S2"}
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?$")

# Legacy -> formal field mapping
LEGACY_FIELD_MAP: dict[str, str] = {
    "golden_answer": "expected_answer",
    "expected_chunks": "expected_evidence",
    "min_pass_rate": "min_case_score",
}

# ======================================================================
# ReviewCase — lightweight review output
# ======================================================================


@dataclass
class ReviewCase:
    """Lightweight review output from case generation.

    This is intentionally minimal; fields not present here are
    filled by the mapper when promoting to the formal schema.
    """

    title: str
    question: str
    expected_answer: str = ""
    expected_evidence: str = ""
    severity: str = "S2"
    category: str = ""
    notes: str = ""


# ======================================================================
# Mapper / Normalizer
# ======================================================================


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def classify_review_status(review: ReviewCase) -> str:
    """Determine initial status for a ReviewCase being promoted to formal schema.

    Returns 'needs_review' when the case is ambiguous or incomplete,
    'draft' otherwise.  Never returns 'active' — that requires human review.

    Conditions for needs_review:
    - question is empty or very short (< 5 chars)
    - expected_answer is empty (cannot evaluate without expected answer)
    - expected_evidence is empty (no grounding reference)
    - severity is missing or invalid
    """
    reasons: list[str] = []

    question = (review.question or "").strip()
    if not question:
        reasons.append("question空")
    elif len(question) < 5:
        reasons.append("question短すぎ")

    if not (review.expected_answer or "").strip():
        reasons.append("expected_answer空")

    if not (review.expected_evidence or "").strip():
        reasons.append("expected_evidence空")

    severity = (review.severity or "").strip().upper()
    if severity not in VALID_SEVERITIES:
        reasons.append(f"severity不正({review.severity})")

    if reasons:
        return "needs_review"
    return "draft"


def review_case_to_formal_row(
    review: ReviewCase,
    *,
    case_id: str = "",
    default_owner: str = "",
    default_status: str | None = None,
) -> dict[str, str]:
    """Map a ReviewCase to a formal cases.csv row dict.

    - title -> name
    - Missing fields filled with safe defaults
    - case_id left empty if not provided (to be assigned downstream)
    - source_doc absence noted in notes
    - If default_status is None, auto-classify via classify_review_status()
    """
    severity = review.severity.upper() if review.severity else "S2"
    if severity not in VALID_SEVERITIES:
        severity = "S2"

    if default_status is not None:
        status = default_status if default_status in VALID_STATUSES else "draft"
    else:
        status = classify_review_status(review)

    notes_parts: list[str] = []
    if review.notes:
        notes_parts.append(review.notes)
    notes_parts.append("source_doc未設定")

    default_score = "100" if severity == "S1" else "85"

    return {
        "case_id": case_id,
        "name": review.title.strip() if review.title else "",
        "status": status,
        "severity": severity,
        "question": review.question.strip() if review.question else "",
        "expected_answer": review.expected_answer.strip() if review.expected_answer else "",
        "expected_evidence": review.expected_evidence.strip() if review.expected_evidence else "",
        "category": (review.category.strip() if review.category else "") or "general",
        "source_doc": "",
        "owner": default_owner,
        "min_case_score": default_score,
        "updated_at": _now_iso(),
        "last_reviewed_at": "",
        "notes": "; ".join(notes_parts),
    }


def review_row_to_review_case(row: dict[str, str]) -> ReviewCase:
    """Convert a raw CSV row dict (from review output) into a ReviewCase."""
    return ReviewCase(
        title=_clean(row.get("title") or row.get("name") or ""),
        question=_clean(row.get("question") or ""),
        expected_answer=_clean(row.get("expected_answer") or row.get("golden_answer") or ""),
        expected_evidence=_clean(row.get("expected_evidence") or row.get("expected_chunks") or ""),
        severity=_clean(row.get("severity") or row.get("risk_level") or "S2"),
        category=_clean(row.get("category") or ""),
        notes=_clean(row.get("notes") or ""),
    )


def normalize_legacy_row(row: dict[str, str]) -> dict[str, str]:
    """Normalize a row that may contain legacy field names to formal names.

    Handles:
        golden_answer   -> expected_answer
        expected_chunks -> expected_evidence
        min_pass_rate   -> min_case_score

    Also injects 'status' and 'updated_at' if missing.
    """
    result: dict[str, str] = {}
    for key, value in row.items():
        formal_key = LEGACY_FIELD_MAP.get(key, key)
        # Don't overwrite a formal key already set explicitly
        if formal_key in result and result[formal_key]:
            continue
        result[formal_key] = _clean(value)

    # Ensure all formal fields exist
    for f in FORMAL_CASE_FIELDS:
        result.setdefault(f, "")

    # Fill defaults for new mandatory fields
    if not result["status"]:
        result["status"] = "active"
    if not result["updated_at"]:
        result["updated_at"] = _now_iso()

    # source_doc: migrate from expected_evidence path hints if possible
    if not result["source_doc"] and result["expected_evidence"]:
        first_ev = result["expected_evidence"].split(";")[0].strip()
        if "/" in first_ev:
            # e.g. "packs/hr/documents/doc.md#sec-1" -> "packs/hr/documents/doc.md"
            result["source_doc"] = first_ev.split("#")[0]

    return result


# ======================================================================
# Validation
# ======================================================================


@dataclass
class ValidationError:
    """A single validation failure."""

    case_id: str
    field: str
    message: str
    level: Literal["error", "warn"] = "error"


def validate_case_row(row: dict[str, str]) -> list[ValidationError]:
    """Validate a formal case row dict. Returns empty list if valid."""
    errors: list[ValidationError] = []
    case_id = row.get("case_id", "").strip()
    cid = case_id or "(empty)"

    # case_id non-empty
    if not case_id:
        errors.append(ValidationError(cid, "case_id", "case_idが空です"))

    # question non-empty
    if not row.get("question", "").strip():
        errors.append(ValidationError(cid, "question", "questionが空です"))

    # expected_answer non-empty (error for active, warn for draft/needs_review)
    if not row.get("expected_answer", "").strip():
        status_val = row.get("status", "").strip()
        if status_val == "active":
            errors.append(
                ValidationError(cid, "expected_answer", "activeケースのexpected_answerが空です")
            )
        else:
            errors.append(
                ValidationError(cid, "expected_answer", "expected_answerが空です", "warn")
            )

    # status in valid set
    status = row.get("status", "").strip()
    if status and status not in VALID_STATUSES:
        errors.append(
            ValidationError(
                cid,
                "status",
                f"無効なstatus: '{status}' (許容値: {', '.join(sorted(VALID_STATUSES))})",
            )
        )

    # severity in valid set
    severity = row.get("severity", "").strip().upper()
    if severity and severity not in VALID_SEVERITIES:
        errors.append(
            ValidationError(
                cid,
                "severity",
                f"無効なseverity: '{severity}' (許容値: {', '.join(sorted(VALID_SEVERITIES))})",
            )
        )

    # min_case_score numeric and in range
    score_str = row.get("min_case_score", "").strip()
    if score_str:
        try:
            score = float(score_str)
            if score < 0 or score > 100:
                errors.append(
                    ValidationError(cid, "min_case_score", f"範囲外の値: {score} (0-100)")
                )
        except ValueError:
            errors.append(ValidationError(cid, "min_case_score", f"数値でない値: '{score_str}'"))

    # expected_evidence format
    ev = row.get("expected_evidence", "").strip()
    if ev:
        for part in ev.split(";"):
            part = part.strip()
            if not part:
                continue
            # Warn on clearly wrong patterns (e.g. bare numbers)
            if part.isdigit():
                errors.append(
                    ValidationError(
                        cid,
                        "expected_evidence",
                        f"不正な形式のevidence: '{part}' (数値のみ)",
                        "warn",
                    )
                )

    # date format checks
    for date_field in ("updated_at", "last_reviewed_at"):
        val = row.get(date_field, "").strip()
        if val and not _ISO_DATE_RE.match(val):
            errors.append(
                ValidationError(cid, date_field, f"日付形式が不正: '{val}' (YYYY-MM-DD 想定)")
            )

    return errors


def validate_case_rows(rows: list[dict[str, str]]) -> list[ValidationError]:
    """Validate a list of formal case rows including duplicates check."""
    errors: list[ValidationError] = []
    seen_ids: set[str] = set()

    for row in rows:
        errors.extend(validate_case_row(row))
        cid = row.get("case_id", "").strip()
        if cid:
            if cid in seen_ids:
                errors.append(ValidationError(cid, "case_id", f"case_id重複: '{cid}'"))
            seen_ids.add(cid)

    return errors


# ======================================================================
# Helpers
# ======================================================================


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


# ======================================================================
# Pipeline: review → formal with validation
# ======================================================================


@dataclass
class PromotionResult:
    """Result of promoting a batch of ReviewCases to formal rows."""

    rows: list[dict[str, str]]
    validation_errors: list[ValidationError]
    needs_review_count: int
    draft_count: int

    @property
    def has_errors(self) -> bool:
        return any(e.level == "error" for e in self.validation_errors)


def promote_review_cases(
    reviews: list[ReviewCase],
    *,
    id_prefix: str = "GEN",
    id_start: int = 1,
    default_owner: str = "",
) -> PromotionResult:
    """End-to-end pipeline: review cases → formal rows with validation.

    1. classify_review_status() determines initial status
    2. review_case_to_formal_row() maps to formal schema
    3. validate_case_rows() checks for errors

    Case IDs are auto-generated as {id_prefix}{ordinal:03d}.
    """
    rows: list[dict[str, str]] = []
    for i, review in enumerate(reviews):
        case_id = f"{id_prefix}{id_start + i:03d}"
        row = review_case_to_formal_row(
            review,
            case_id=case_id,
            default_owner=default_owner,
        )
        rows.append(row)

    errors = validate_case_rows(rows)

    needs_review_count = sum(1 for r in rows if r.get("status") == "needs_review")
    draft_count = sum(1 for r in rows if r.get("status") == "draft")

    return PromotionResult(
        rows=rows,
        validation_errors=errors,
        needs_review_count=needs_review_count,
        draft_count=draft_count,
    )
