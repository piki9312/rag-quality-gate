"""Vendor review YAML flow for generated draft cases."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from rqg.quality.case_merge import load_csv_rows, write_cases_csv
from rqg.quality.case_schema import (
    FORMAL_CASE_FIELDS,
    VALID_EVAL_MODES,
    VALID_SEVERITIES,
    validate_case_rows,
)

REVIEW_FLOW_VERSION = 1
REVIEW_FLOW_GENERATOR = "proof_gate_review_flow"
VALID_REVIEW_DECISIONS = {"pending", "approve", "reject"}
UNAPPROVED_DRAFT_MARKER = "answer_status:unapproved-draft"
VENDOR_APPROVED_MARKER = "answer_status:vendor-approved"


def export_case_review_artifacts(
    draft_path: str | Path,
    *,
    output_yaml: str | Path,
    output_md: str | Path,
) -> tuple[Path, Path]:
    """Export structured YAML and Markdown preview from a draft cases.csv."""
    rows = load_csv_rows(draft_path)
    payload = build_review_cases_payload(rows)
    yaml_path = write_review_cases_yaml(payload, output_yaml)
    md_path = write_review_cases_markdown(payload, output_md)
    return yaml_path, md_path


def build_review_cases_payload(rows: Sequence[Mapping[str, str]]) -> dict[str, object]:
    """Build the vendor-owned YAML review payload for needs_review draft rows."""
    review_cases: list[dict[str, object]] = []
    for row in rows:
        normalized = _normalize_draft_row(row)
        if normalized["status"] != "needs_review":
            raise ValueError("export-case-review only accepts status=needs_review draft rows")
        notes = normalized["notes"]
        review_cases.append(
            {
                "case_id": normalized["case_id"],
                "decision": "pending",
                "status": "needs_review",
                "suggestion": {
                    "name": normalized["name"],
                    "question": normalized["question"],
                    "intent": _extract_note_value(notes, "intent") or normalized["category"],
                    "failure_pattern": _extract_failure_pattern(notes),
                    "severity_hint": normalized["severity"],
                    "evidence_requirement": _split_semicolon(normalized["expected_evidence"]),
                    "expected_behavior_template": _expected_behavior_template(normalized),
                },
                "vendor_review": {
                    "expected_answer": normalized["expected_answer"],
                    "expected_evidence": _split_semicolon(normalized["expected_evidence"]),
                    "expected_keywords": _split_semicolon(normalized["expected_keywords"]),
                    "severity": normalized["severity"],
                    "eval_mode": normalized["eval_mode"],
                    "reviewed_by": "",
                    "reviewed_at": "",
                    "notes": "",
                },
            }
        )
    return {
        "version": REVIEW_FLOW_VERSION,
        "generated_by": REVIEW_FLOW_GENERATOR,
        "cases": review_cases,
    }


def write_review_cases_yaml(payload: Mapping[str, object], path: str | Path) -> Path:
    """Write review_cases.yaml."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(dict(payload), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return output_path


def write_review_cases_markdown(payload: Mapping[str, object], path: str | Path) -> Path:
    """Write human-readable review_cases.md preview."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_review_cases_markdown(payload), encoding="utf-8")
    return output_path


def render_review_cases_markdown(payload: Mapping[str, object]) -> str:
    """Render the review YAML payload as a human-readable preview."""
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("review payload must include cases list")

    lines = ["# ケース下書きレビュー", ""]
    for item in cases:
        if not isinstance(item, dict):
            raise ValueError("review payload case entries must be mappings")
        case_id = str(item.get("case_id") or "").strip()
        decision = str(item.get("decision") or "pending").strip()
        status = str(item.get("status") or "needs_review").strip()
        suggestion = item.get("suggestion") if isinstance(item.get("suggestion"), dict) else {}
        name = str(suggestion.get("name") or case_id).strip()

        lines.extend(
            [
                f"## {case_id}: {name}",
                "",
                f"ステータス: {status}",
                f"レビュー判断: {decision}",
                f"重大度候補: {suggestion.get('severity_hint', '')}",
                "",
                "確認意図:",
                str(suggestion.get("intent") or ""),
                "",
                "失敗パターン:",
                str(suggestion.get("failure_pattern") or ""),
                "",
                "質問案:",
                str(suggestion.get("question") or ""),
                "",
                "期待される回答の型:",
            ]
        )
        lines.extend(_markdown_list(suggestion.get("expected_behavior_template")))
        lines.extend(["", "必要な根拠:"])
        lines.extend(_markdown_list(suggestion.get("evidence_requirement")))
        lines.extend(
            [
                "",
                "ベンダー確認事項:",
                "- 期待回答（expected_answer）を確認・入力してください",
                "- 根拠情報（expected_evidence）を確認してください",
                "- 重大度（severity）を確定してください",
                "- レビュー判断（decision）を approve / reject / pending から選択してください",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def approve_reviewed_cases(
    *,
    draft_path: str | Path,
    review_path: str | Path,
    output_path: str | Path,
) -> Path:
    """Apply approved review YAML entries to formal cases.csv rows."""
    draft_rows = [_normalize_draft_row(row) for row in load_csv_rows(draft_path)]
    review_payload = load_review_cases_yaml(review_path)
    review_by_id = _review_cases_by_id(review_payload)

    output_rows: list[dict[str, str]] = []
    for draft_row in draft_rows:
        review_case = review_by_id.get(draft_row["case_id"])
        if review_case is None:
            output_rows.append({**draft_row, "status": "needs_review"})
            continue
        output_rows.append(_apply_review_case(draft_row, review_case, review_payload))

    validation_errors = validate_case_rows(output_rows)
    blocking_errors = [error for error in validation_errors if error.level == "error"]
    if blocking_errors:
        first = blocking_errors[0]
        raise ValueError(f"approved cases.csv validation failed: {first.case_id} {first.message}")
    return write_cases_csv(output_path, output_rows)


def load_review_cases_yaml(path: str | Path) -> dict[str, object]:
    """Load and validate review_cases.yaml."""
    review_path = Path(path)
    if not review_path.exists():
        raise FileNotFoundError(f"Review YAML not found: {review_path}")
    try:
        payload = yaml.safe_load(review_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid review YAML: {review_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("review_cases.yaml must be a mapping")
    _validate_review_payload(payload)
    return payload


def _validate_review_payload(payload: Mapping[str, object]) -> None:
    if payload.get("version") != REVIEW_FLOW_VERSION:
        raise ValueError("review_cases.yaml version must be 1")
    if not isinstance(payload.get("generated_by"), str) or not payload.get("generated_by"):
        raise ValueError("review_cases.yaml requires generated_by")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("review_cases.yaml requires cases list")
    for item in cases:
        if not isinstance(item, dict):
            raise ValueError("review_cases.yaml case entries must be mappings")
        case_id = str(item.get("case_id") or "").strip()
        if not case_id:
            raise ValueError("review case requires case_id")
        decision = str(item.get("decision") or "").strip()
        if decision not in VALID_REVIEW_DECISIONS:
            raise ValueError(f"review case {case_id} has invalid decision: {decision}")
        vendor_review = item.get("vendor_review")
        if not isinstance(vendor_review, dict):
            raise ValueError(f"review case {case_id} requires vendor_review")
        severity = str(vendor_review.get("severity") or "").strip().upper()
        if severity and severity not in VALID_SEVERITIES:
            raise ValueError(f"review case {case_id} has invalid severity: {severity}")
        eval_mode = str(vendor_review.get("eval_mode") or "").strip()
        if eval_mode and eval_mode not in VALID_EVAL_MODES:
            raise ValueError(f"review case {case_id} has invalid eval_mode: {eval_mode}")


def _review_cases_by_id(payload: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("review_cases.yaml requires cases list")
    by_id: dict[str, Mapping[str, object]] = {}
    for item in cases:
        if not isinstance(item, dict):
            raise ValueError("review case entries must be mappings")
        case_id = str(item.get("case_id") or "").strip()
        if case_id in by_id:
            raise ValueError(f"duplicate review case_id: {case_id}")
        by_id[case_id] = item
    return by_id


def _apply_review_case(
    draft_row: Mapping[str, str],
    review_case: Mapping[str, object],
    payload: Mapping[str, object],
) -> dict[str, str]:
    decision = str(review_case.get("decision") or "").strip()
    vendor_review = review_case.get("vendor_review")
    if not isinstance(vendor_review, dict):
        raise ValueError(f"review case {draft_row['case_id']} requires vendor_review")

    row = dict(draft_row)
    if decision == "pending":
        row["status"] = "needs_review"
        return row
    if decision == "reject":
        row["status"] = "deprecated"
        row["notes"] = _merge_notes(row["notes"], "review_decision:reject")
        return row
    if decision != "approve":
        raise ValueError(f"unsupported review decision: {decision}")

    expected_answer = _clean(vendor_review.get("expected_answer"))
    expected_evidence = _join_list(vendor_review.get("expected_evidence"))
    expected_keywords = _join_list(vendor_review.get("expected_keywords"))
    severity = _clean(vendor_review.get("severity")).upper()
    eval_mode = _clean(vendor_review.get("eval_mode"))
    reviewed_by = _clean(vendor_review.get("reviewed_by"))
    reviewed_at = _clean(vendor_review.get("reviewed_at"))

    if not expected_answer:
        raise ValueError(f"approved case {draft_row['case_id']} requires expected_answer")
    if not expected_evidence:
        raise ValueError(f"approved case {draft_row['case_id']} requires expected_evidence")
    if not severity or severity not in VALID_SEVERITIES:
        raise ValueError(f"approved case {draft_row['case_id']} requires valid severity")
    if not eval_mode or eval_mode not in VALID_EVAL_MODES:
        raise ValueError(f"approved case {draft_row['case_id']} requires valid eval_mode")

    row.update(
        {
            "status": "active",
            "expected_answer": expected_answer,
            "expected_evidence": expected_evidence,
            "expected_keywords": expected_keywords,
            "severity": severity,
            "eval_mode": eval_mode,
            "last_reviewed_at": reviewed_at,
        }
    )
    if reviewed_by and not row.get("owner"):
        row["owner"] = reviewed_by

    suggestion = (
        review_case.get("suggestion") if isinstance(review_case.get("suggestion"), dict) else {}
    )
    row["notes"] = _merge_notes(
        _remove_note_markers(row["notes"], {UNAPPROVED_DRAFT_MARKER}),
        _clean(vendor_review.get("notes")),
        "review_decision:approve",
        VENDOR_APPROVED_MARKER,
        f"approved_by:{reviewed_by}" if reviewed_by else "",
        f"intent:{_clean(suggestion.get('intent'))}" if _clean(suggestion.get("intent")) else "",
        (
            f"failure_pattern:{_clean(suggestion.get('failure_pattern'))}"
            if _clean(suggestion.get("failure_pattern"))
            else ""
        ),
        f"generated_by:{_clean(payload.get('generated_by'))}",
    )
    return row


def _normalize_draft_row(row: Mapping[str, str]) -> dict[str, str]:
    normalized = {field: _clean(row.get(field)) for field in FORMAL_CASE_FIELDS}
    if not normalized["case_id"]:
        raise ValueError("draft case row requires case_id")
    if not normalized["name"]:
        normalized["name"] = normalized["case_id"]
    normalized["status"] = normalized["status"] or "needs_review"
    normalized["severity"] = (normalized["severity"] or "S2").upper()
    return normalized


def _expected_behavior_template(row: Mapping[str, str]) -> list[str]:
    eval_mode = row.get("eval_mode", "")
    template: list[str] = []
    if row.get("expected_answer"):
        template.append("include_expected_answer")
    if row.get("expected_evidence"):
        template.append("cite_expected_evidence")
    if row.get("expected_keywords"):
        template.append("include_expected_keywords")
    if eval_mode and eval_mode not in template:
        template.append(eval_mode)
    return template


def _extract_failure_pattern(notes: str) -> str:
    return _extract_note_value(notes, "failure_pattern") or _extract_note_value(notes, "pattern")


def _extract_note_value(notes: str, key: str) -> str:
    prefix = f"{key}:"
    for part in notes.split(";"):
        marker = part.strip()
        if marker.startswith(prefix):
            return marker[len(prefix) :].strip()
    return ""


def _split_semicolon(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [_clean(item) for item in raw if _clean(item)]
    return [item.strip() for item in _clean(raw).split(";") if item.strip()]


def _join_list(raw: object) -> str:
    return ";".join(_split_semicolon(raw))


def _markdown_list(raw: object) -> list[str]:
    items = _split_semicolon(raw)
    if not items:
        return ["-"]
    return [f"- {item}" for item in items]


def _merge_notes(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        for part in _clean(value).split(";"):
            marker = part.strip()
            if marker and marker not in parts:
                parts.append(marker)
    return "; ".join(parts)


def _remove_note_markers(notes: str, markers_to_remove: set[str]) -> str:
    parts = [
        part.strip()
        for part in _clean(notes).split(";")
        if part.strip() and part.strip() not in markers_to_remove
    ]
    return "; ".join(parts)


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
