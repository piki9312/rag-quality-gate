"""Case schema definitions, mapper/normalizer, and validation.

This module separates review lightweight output from the formal cases.csv
schema and provides a clean mapping layer between them.

Design principles:
- review (lightweight 10 fields) ≠ cases.csv (formal 16 fields)
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
    "eval_mode",
    "question",
    "expected_answer",
    "expected_evidence",
    "expected_keywords",
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
    "eval_mode",
    "expected_answer",
    "expected_evidence",
    "expected_keywords",
    "source_doc",
    "severity",
    "category",
    "notes",
]

VALID_STATUSES = {"draft", "active", "needs_review", "deprecated"}
VALID_SEVERITIES = {"S1", "S2"}
VALID_EVAL_MODES = {"exact", "evidence_keyword", "grounded_judge"}
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?$")
_QUESTION_WHITESPACE_RE = re.compile(r"\s+")
_ORDINAL_PREFIX_RE = re.compile(r"^\d+\s*[.)．、）]\s*")
_NOTE_PARTS_RE = re.compile(r"\s*;\s*")

_QUESTION_TYPE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "contact",
        (
            "問い合わせ先",
            "窓口",
            "連絡先",
            "エスカレーション",
            "who must be contacted",
            "who should be contacted",
            "contacted first",
        ),
    ),
    ("exception", ("例外", "exception condition", "exception conditions")),
    ("list", ("主な", "要点", "事由", "reasons", "注意事項", "概要", "ポイント")),
    ("amount", ("いくら", "何円", "月額", "amount", "cost")),
    (
        "deadline",
        (
            "いつ",
            "期限",
            "締め日",
            "何日",
            "いつまで",
            "when should",
            "how often",
            "cadence",
        ),
    ),
    (
        "procedure",
        (
            "手順",
            "方法",
            "どのように",
            "どうやって",
            "申請方法",
            "how should",
            "how to submit",
            "how to apply",
            "submit through",
            "request method",
        ),
    ),
    (
        "policy",
        (
            "条件",
            "ルール",
            "required",
            "requirement",
            "what is required",
            "what are the requirements",
            "what is the rule",
            "what are the rules",
            "必要な証憑",
            "必要書類",
            "必要なもの",
            "承認条件",
        ),
    ),
)

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
    eval_mode: str = ""
    expected_answer: str = ""
    expected_evidence: str = ""
    expected_keywords: str = ""
    source_doc: str = ""
    severity: str = "S2"
    category: str = ""
    notes: str = ""


# ======================================================================
# Mapper / Normalizer
# ======================================================================


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def normalize_eval_mode(value: object) -> str:
    return _clean(value).lower().replace("-", "_")


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, set)):
        return any(_clean(item) for item in value)
    return bool(_clean(value))


def _note_parts(notes: object) -> list[str]:
    cleaned = _clean(notes)
    if not cleaned:
        return []
    return [part for part in _NOTE_PARTS_RE.split(cleaned) if part]


def has_note_marker(notes: object, marker: str) -> bool:
    return marker in _note_parts(notes)


def has_note_marker_prefix(notes: object, prefix: str) -> bool:
    return any(part.startswith(prefix) for part in _note_parts(notes))


def is_auto_expected_answer_draft(notes: object) -> bool:
    return has_note_marker(notes, "auto_expected_answer_status:draft")


def infer_review_eval_mode(
    *,
    eval_mode: object = "",
    expected_answer: object = "",
    expected_evidence: object = "",
    expected_keywords: object = "",
    notes: object = "",
) -> str:
    normalized_eval_mode = normalize_eval_mode(eval_mode)
    if normalized_eval_mode in VALID_EVAL_MODES:
        return normalized_eval_mode
    inferred_expected_answer = "" if is_auto_expected_answer_draft(notes) else expected_answer
    return infer_eval_mode(
        expected_answer=inferred_expected_answer,
        expected_evidence=expected_evidence,
        expected_keywords=expected_keywords,
    )


def infer_eval_mode(
    *,
    expected_answer: object = "",
    expected_evidence: object = "",
    expected_keywords: object = "",
) -> str:
    if _has_value(expected_answer):
        return "exact"
    if _has_value(expected_keywords):
        return "evidence_keyword"
    if _has_value(expected_evidence):
        return "grounded_judge"
    return ""


def strip_ordinal_prefix(text: object) -> str:
    return _ORDINAL_PREFIX_RE.sub("", _clean(text), count=1)


def _first_evidence_token(expected_evidence: object) -> str:
    if isinstance(expected_evidence, (list, tuple, set)):
        for item in expected_evidence:
            token = _clean(item)
            if token:
                return token
        return ""

    for item in _clean(expected_evidence).split(";"):
        token = item.strip()
        if token:
            return token
    return ""


def infer_source_doc(
    *,
    expected_evidence: object = "",
    source_doc: object = "",
    doc_snapshot_id: object = "",
) -> str:
    first_evidence = _first_evidence_token(expected_evidence)
    if first_evidence and ("/" in first_evidence or "\\" in first_evidence):
        return first_evidence.split("#", 1)[0]

    existing_source_doc = _clean(source_doc)
    if existing_source_doc:
        return existing_source_doc

    return _clean(doc_snapshot_id)


def infer_question_types(question: str) -> tuple[str, ...]:
    normalized = _QUESTION_WHITESPACE_RE.sub(" ", (question or "").strip().lower())
    detected: list[str] = []
    for label, patterns in _QUESTION_TYPE_PATTERNS:
        if any(pattern in normalized for pattern in patterns):
            detected.append(label)
    return tuple(detected)


def is_mixed_question(question: str) -> bool:
    return len(set(infer_question_types(question))) >= 2


def classify_review_status(review: ReviewCase) -> str:
    """Determine initial status for a ReviewCase being promoted to formal schema.

    Returns 'needs_review' when the case is ambiguous or incomplete,
    'draft' otherwise.  Never returns 'active' — that requires human review.

    Conditions for needs_review:
    - question is empty or very short (< 5 chars)
    - eval_mode is invalid
    - exact requires expected_answer
    - evidence_keyword requires expected_evidence and expected_keywords
    - grounded_judge requires expected_evidence
    - unresolved legacy rows still require expected_answer and expected_evidence
    - severity is missing or invalid
    """
    reasons: list[str] = []

    question = (review.question or "").strip()
    if not question:
        reasons.append("question空")
    elif len(question) < 5:
        reasons.append("question短すぎ")
    elif is_mixed_question(question):
        reasons.append(f"question問い型混在({','.join(infer_question_types(question))})")

    raw_eval_mode = normalize_eval_mode(review.eval_mode)
    if raw_eval_mode and raw_eval_mode not in VALID_EVAL_MODES:
        reasons.append(f"eval_mode不正({review.eval_mode})")

    effective_eval_mode = infer_review_eval_mode(
        eval_mode=review.eval_mode,
        expected_answer=review.expected_answer,
        expected_evidence=review.expected_evidence,
        expected_keywords=review.expected_keywords,
        notes=review.notes,
    )

    if effective_eval_mode == "exact":
        if not (review.expected_answer or "").strip():
            reasons.append("expected_answer空")
    elif effective_eval_mode == "evidence_keyword":
        if not (review.expected_evidence or "").strip():
            reasons.append("expected_evidence空")
        if not (review.expected_keywords or "").strip():
            reasons.append("expected_keywords空")
    elif effective_eval_mode == "grounded_judge":
        if not (review.expected_evidence or "").strip():
            reasons.append("expected_evidence空")
    else:
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

    eval_mode = infer_review_eval_mode(
        eval_mode=review.eval_mode,
        expected_answer=review.expected_answer,
        expected_evidence=review.expected_evidence,
        expected_keywords=review.expected_keywords,
        notes=review.notes,
    )

    if default_status is not None:
        status = default_status if default_status in VALID_STATUSES else "draft"
    else:
        status = classify_review_status(review)
    if is_auto_expected_answer_draft(review.notes) and status == "active":
        status = "draft"

    source_doc = infer_source_doc(
        expected_evidence=review.expected_evidence,
        source_doc=review.source_doc,
    )

    notes_parts: list[str] = []
    if review.notes:
        notes_parts.append(review.notes)
    question_types = infer_question_types(review.question)
    if len(set(question_types)) >= 2:
        notes_parts.append(f"mixed_question:{','.join(question_types)}")
    if not source_doc:
        notes_parts.append("source_doc未設定")

    default_score = "100" if severity == "S1" else "85"

    return {
        "case_id": case_id,
        "name": review.title.strip() if review.title else "",
        "status": status,
        "severity": severity,
        "eval_mode": eval_mode,
        "question": review.question.strip() if review.question else "",
        "expected_answer": review.expected_answer.strip() if review.expected_answer else "",
        "expected_evidence": review.expected_evidence.strip() if review.expected_evidence else "",
        "expected_keywords": review.expected_keywords.strip() if review.expected_keywords else "",
        "category": (review.category.strip() if review.category else "") or "general",
        "source_doc": source_doc,
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
        eval_mode=_clean(row.get("eval_mode") or ""),
        expected_answer=_clean(row.get("expected_answer") or row.get("golden_answer") or ""),
        expected_evidence=_clean(row.get("expected_evidence") or row.get("expected_chunks") or ""),
        expected_keywords=_clean(row.get("expected_keywords") or ""),
        source_doc=_clean(row.get("source_doc") or ""),
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

    if result["eval_mode"]:
        result["eval_mode"] = normalize_eval_mode(result["eval_mode"])

    # Fill defaults for new mandatory fields
    if not result["status"]:
        result["status"] = "active"
    if not result["updated_at"]:
        result["updated_at"] = _now_iso()

    # source_doc is a helper field derived from evidence path hints when possible.
    result["source_doc"] = infer_source_doc(
        expected_evidence=result["expected_evidence"],
        source_doc=result["source_doc"],
    )

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


def _required_field_level(status: str) -> Literal["error", "warn"]:
    return "error" if status == "active" else "warn"


def _append_required_field_error(
    errors: list[ValidationError],
    case_id: str,
    *,
    field: str,
    status: str,
    eval_mode: str,
) -> None:
    level = _required_field_level(status)
    prefix = "active " if level == "error" else ""
    errors.append(
        ValidationError(case_id, field, f"{prefix}{eval_mode}ケースの{field}が空です", level)
    )


def validate_case_row(
    row: dict[str, str],
    *,
    require_active_owner: bool = False,
) -> list[ValidationError]:
    """Validate a formal case row dict. Returns empty list if valid."""
    errors: list[ValidationError] = []
    case_id = row.get("case_id", "").strip()
    cid = case_id or "(empty)"
    status = row.get("status", "").strip()
    raw_eval_mode = normalize_eval_mode(row.get("eval_mode", ""))
    notes = row.get("notes", "")
    effective_eval_mode = infer_review_eval_mode(
        eval_mode=raw_eval_mode,
        expected_answer=row.get("expected_answer", ""),
        expected_evidence=row.get("expected_evidence", ""),
        expected_keywords=row.get("expected_keywords", ""),
        notes=notes,
    )

    # case_id non-empty
    if not case_id:
        errors.append(ValidationError(cid, "case_id", "case_idが空です"))

    # status in valid set
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

    # eval_mode in valid set
    if raw_eval_mode and raw_eval_mode not in VALID_EVAL_MODES:
        errors.append(
            ValidationError(
                cid,
                "eval_mode",
                f"無効なeval_mode: '{raw_eval_mode}' (許容値: {', '.join(sorted(VALID_EVAL_MODES))})",
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

    # date format checks
    for date_field in ("updated_at", "last_reviewed_at"):
        val = row.get(date_field, "").strip()
        if val and not _ISO_DATE_RE.match(val):
            errors.append(
                ValidationError(cid, date_field, f"日付形式が不正: '{val}' (YYYY-MM-DD 想定)")
            )

    if status == "deprecated":
        return errors

    if require_active_owner and status == "active" and not row.get("owner", "").strip():
        errors.append(
            ValidationError(
                cid,
                "owner",
                "active case owner is required when staleness policy is enabled",
            )
        )

    if status == "active" and is_auto_expected_answer_draft(notes):
        errors.append(
            ValidationError(
                cid,
                "notes",
                "auto-generated expected_answer draft must be manually reviewed before active",
            )
        )

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

    # question non-empty
    if not row.get("question", "").strip():
        errors.append(ValidationError(cid, "question", "questionが空です"))

    if effective_eval_mode == "exact":
        if not row.get("expected_answer", "").strip():
            _append_required_field_error(
                errors,
                cid,
                field="expected_answer",
                status=status,
                eval_mode="exact",
            )
    elif effective_eval_mode == "evidence_keyword":
        if not row.get("expected_evidence", "").strip():
            _append_required_field_error(
                errors,
                cid,
                field="expected_evidence",
                status=status,
                eval_mode="evidence_keyword",
            )
        if not row.get("expected_keywords", "").strip():
            _append_required_field_error(
                errors,
                cid,
                field="expected_keywords",
                status=status,
                eval_mode="evidence_keyword",
            )
    elif effective_eval_mode == "grounded_judge":
        if not row.get("expected_evidence", "").strip():
            _append_required_field_error(
                errors,
                cid,
                field="expected_evidence",
                status=status,
                eval_mode="grounded_judge",
            )
    elif not row.get("expected_answer", "").strip():
        level = _required_field_level(status)
        errors.append(ValidationError(cid, "expected_answer", "expected_answerが空です", level))

    return errors


def validate_case_rows(
    rows: list[dict[str, str]],
    *,
    require_active_owner: bool = False,
) -> list[ValidationError]:
    """Validate a list of formal case rows including duplicates check."""
    errors: list[ValidationError] = []
    seen_ids: set[str] = set()

    for row in rows:
        errors.extend(validate_case_row(row, require_active_owner=require_active_owner))
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
