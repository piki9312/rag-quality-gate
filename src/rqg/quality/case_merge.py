"""Helpers to merge generated review CSV into operations cases.csv."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .case_schema import (
    FORMAL_CASE_FIELDS,
    LEGACY_FIELD_MAP,
    normalize_legacy_row,
)

AUTO_UPDATE_FIELDS = ("question", "expected_evidence", "expected_keywords")
_SPACE_RE = re.compile(r"\s+")
_ORDINAL_PREFIX_RE = re.compile(r"^\d+\.\s*")


@dataclass
class CaseMergeSummary:
    base_cases: int
    review_cases: int
    merged_cases: int
    added_case_ids: list[str] = field(default_factory=list)
    updated_case_ids: list[str] = field(default_factory=list)
    unchanged_case_ids: list[str] = field(default_factory=list)
    duplicate_review_case_ids: list[str] = field(default_factory=list)
    matched_by_content_review_case_ids: list[str] = field(default_factory=list)


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_severity(value: object) -> str:
    severity = _clean(value).upper()
    if severity in {"S1", "S2"}:
        return severity
    return "S2"


def _normalize_semicolon_list(raw: object) -> str:
    cleaned: list[str] = []
    for item in _clean(raw).split(";"):
        token = item.strip()
        if token and token not in cleaned:
            cleaned.append(token)
    return ";".join(cleaned)


def _normalize_question_for_signature(raw: object) -> str:
    question = _clean(raw)
    question = _ORDINAL_PREFIX_RE.sub("", question)
    question = _SPACE_RE.sub(" ", question)
    return question.strip().lower()


def _content_signature(row: dict[str, str]) -> str:
    question_key = _normalize_question_for_signature(row.get("question"))
    evidence_key = _normalize_semicolon_list(
        row.get("expected_evidence") or row.get("expected_chunks")
    ).lower()
    if not question_key and not evidence_key:
        return ""
    return f"{question_key}||{evidence_key}"


def _apply_review_updates_to_existing_row(
    target_row: dict[str, str], review_row: dict[str, str]
) -> bool:
    changed = False

    for field in AUTO_UPDATE_FIELDS:
        candidate = review_row.get(field, "")
        if candidate and candidate != target_row.get(field, ""):
            target_row[field] = candidate
            changed = True

    for field in (
        "name",
        "severity",
        "expected_answer",
        "category",
        "source_doc",
        "owner",
        "min_case_score",
        "last_reviewed_at",
    ):
        if not target_row.get(field) and review_row.get(field):
            target_row[field] = review_row[field]
            changed = True

    return changed


def _default_min_case_score(severity: str) -> str:
    return "100" if severity == "S1" else "85"


def _normalize_min_case_score(raw: object, severity: str) -> str:
    value = _clean(raw)
    if not value:
        return _default_min_case_score(severity)
    try:
        numeric = float(value)
    except ValueError:
        return value
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:g}"


def _normalize_base_row(row: dict[str, str]) -> dict[str, str]:
    """Normalize a base cases.csv row, handling both legacy and formal field names."""
    # Apply legacy field renames first
    mapped = normalize_legacy_row(row)

    case_id = _clean(mapped.get("case_id"))
    if not case_id:
        raise ValueError("Base cases CSV includes empty case_id")

    severity = _normalize_severity(mapped.get("severity"))
    normalized = {
        "case_id": case_id,
        "name": _clean(mapped.get("name")) or case_id,
        "status": _clean(mapped.get("status")) or "active",
        "severity": severity,
        "question": _clean(mapped.get("question")),
        "expected_answer": _clean(mapped.get("expected_answer")),
        "expected_evidence": _normalize_semicolon_list(mapped.get("expected_evidence")),
        "expected_keywords": _normalize_semicolon_list(mapped.get("expected_keywords")),
        "category": _clean(mapped.get("category")) or "general",
        "source_doc": _clean(mapped.get("source_doc")),
        "owner": _clean(mapped.get("owner")),
        "min_case_score": _normalize_min_case_score(mapped.get("min_case_score"), severity),
        "updated_at": _clean(mapped.get("updated_at")),
        "last_reviewed_at": _clean(mapped.get("last_reviewed_at")),
        "notes": _clean(mapped.get("notes")),
    }
    return normalized


def _review_to_ops_row(row: dict[str, str]) -> dict[str, str]:
    """Convert a review CSV row into a formal cases.csv row dict.

    Handles legacy field names (expected_chunks, golden_answer, min_pass_rate,
    risk_level) for backward compatibility.
    """
    case_id = _clean(row.get("case_id"))
    if not case_id:
        raise ValueError("Review CSV includes empty case_id")

    severity = _normalize_severity(row.get("severity") or row.get("risk_level"))
    expected_evidence = _normalize_semicolon_list(
        row.get("expected_evidence") or row.get("expected_chunks")
    )
    normalized = {
        "case_id": case_id,
        "name": _clean(row.get("name") or row.get("title")) or case_id,
        "status": _clean(row.get("status")) or "draft",
        "severity": severity,
        "question": _clean(row.get("question")),
        "expected_answer": _clean(row.get("expected_answer") or row.get("golden_answer")),
        "expected_evidence": expected_evidence,
        "expected_keywords": _normalize_semicolon_list(row.get("expected_keywords")),
        "category": _clean(row.get("category")) or "general",
        "source_doc": _clean(row.get("source_doc") or row.get("doc_snapshot_id")),
        "owner": _clean(row.get("owner")),
        "min_case_score": _normalize_min_case_score(
            row.get("min_case_score") or row.get("min_pass_rate"), severity
        ),
        "updated_at": _clean(row.get("updated_at")),
        "last_reviewed_at": _clean(row.get("last_reviewed_at")),
        "notes": _clean(row.get("notes")),
    }
    return normalized


def load_csv_rows(path: str | Path) -> list[dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def merge_cases_rows(
    base_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], CaseMergeSummary]:
    normalized_review_by_id: dict[str, dict[str, str]] = {}
    review_order: list[str] = []
    duplicate_review_case_ids: list[str] = []

    for row in review_rows:
        normalized = _review_to_ops_row(row)
        case_id = normalized["case_id"]
        if case_id in normalized_review_by_id:
            duplicate_review_case_ids.append(case_id)
        else:
            review_order.append(case_id)
        normalized_review_by_id[case_id] = normalized

    merged_rows: list[dict[str, str]] = []
    added_case_ids: list[str] = []
    updated_case_ids: list[str] = []
    unchanged_case_ids: list[str] = []
    matched_by_content_review_case_ids: list[str] = []
    signature_to_merged_index: dict[str, int] = {}

    for base_row in base_rows:
        merged_row = _normalize_base_row(base_row)
        case_id = merged_row["case_id"]
        review_row = normalized_review_by_id.pop(case_id, None)

        if review_row is None:
            merged_rows.append(merged_row)
            unchanged_case_ids.append(case_id)
            signature = _content_signature(merged_row)
            if signature and signature not in signature_to_merged_index:
                signature_to_merged_index[signature] = len(merged_rows) - 1
            continue

        changed = _apply_review_updates_to_existing_row(merged_row, review_row)

        merged_rows.append(merged_row)
        signature = _content_signature(merged_row)
        if signature and signature not in signature_to_merged_index:
            signature_to_merged_index[signature] = len(merged_rows) - 1
        if changed:
            updated_case_ids.append(case_id)
        else:
            unchanged_case_ids.append(case_id)

    for case_id in review_order:
        review_row = normalized_review_by_id.get(case_id)
        if review_row is None:
            continue

        signature = _content_signature(review_row)
        existing_index = signature_to_merged_index.get(signature) if signature else None
        if existing_index is not None:
            existing_row = merged_rows[existing_index]
            existing_case_id = existing_row["case_id"]
            changed = _apply_review_updates_to_existing_row(existing_row, review_row)

            if changed and existing_case_id not in updated_case_ids:
                updated_case_ids.append(existing_case_id)
                if existing_case_id in unchanged_case_ids:
                    unchanged_case_ids.remove(existing_case_id)

            matched_by_content_review_case_ids.append(case_id)
            continue

        merged_rows.append(review_row)
        added_case_ids.append(case_id)
        if signature and signature not in signature_to_merged_index:
            signature_to_merged_index[signature] = len(merged_rows) - 1

    summary = CaseMergeSummary(
        base_cases=len(base_rows),
        review_cases=len(review_rows),
        merged_cases=len(merged_rows),
        added_case_ids=added_case_ids,
        updated_case_ids=updated_case_ids,
        unchanged_case_ids=unchanged_case_ids,
        duplicate_review_case_ids=sorted(set(duplicate_review_case_ids)),
        matched_by_content_review_case_ids=sorted(set(matched_by_content_review_case_ids)),
    )
    return merged_rows, summary


def write_cases_csv(path: str | Path, rows: list[dict[str, str]]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FORMAL_CASE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _clean(row.get(field)) for field in FORMAL_CASE_FIELDS})
    return output_path


def write_merge_report(path: str | Path, summary: CaseMergeSummary) -> Path:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(asdict(summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report_path
