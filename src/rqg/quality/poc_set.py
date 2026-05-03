"""Deterministic Proof Gate PoC case-set builder."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .case_merge import load_csv_rows
from .case_schema import normalize_legacy_row, validate_case_rows

POC_CASE_OUTPUT_FIELDS: list[str] = [
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
    "risk_domain",
    "required_action",
    "evidence_required",
    "owner_role",
    "source_doc",
    "owner",
    "min_case_score",
    "updated_at",
    "last_reviewed_at",
    "notes",
]

_BAND_ORDER = {"S1": 0, "S2": 1, "S3": 2}
_RUNTIME_SEVERITY = {"S1": "S1", "S2": "S2", "S3": "S2"}
_RISK_PROFILE_ALIASES = {
    "customer_support": "customer_support",
    "customer_support_pack": "customer_support",
}
_DEFAULT_RISK_TARGETS = {
    "customer_support": {
        "refund": 5,
        "cancellation": 5,
        "pricing": 6,
        "contract": 6,
        "deadline_procedure": 7,
        "general_faq": 1,
    }
}
_DEFAULT_SOURCE_TARGETS = {
    "customer_support": {
        "S1": [("template", 7), ("generated", 3)],
        "S2": [("generated", 9), ("template", 6)],
        "S3": [("generated", 5)],
    }
}
_DEFAULT_SOURCE_ORDER = {
    "S1": ["template", "generated"],
    "S2": ["generated", "template"],
    "S3": ["generated", "template"],
}
_RISK_DOMAIN_ALIASES = {
    "refund": "refund",
    "refunds": "refund",
    "cancellation": "cancellation",
    "cancel": "cancellation",
    "pricing": "pricing",
    "price": "pricing",
    "contract": "contract",
    "contract_terms": "contract",
    "terms": "contract",
    "deadline": "deadline_procedure",
    "procedure": "deadline_procedure",
    "deadline_procedure": "deadline_procedure",
    "general": "general_faq",
    "faq": "general_faq",
    "general_faq": "general_faq",
    "eligibility": "general_faq",
}


@dataclass(frozen=True)
class PocSetCandidate:
    case_id: str
    name: str
    question: str
    selection_band: str
    output_severity: str
    risk_domain: str
    category: str
    source_type: str
    expected_answer: str
    expected_evidence: tuple[str, ...]
    expected_keywords: tuple[str, ...]
    required_action: str
    notes: str
    question_signature: str
    output_row: dict[str, str]


@dataclass(frozen=True)
class PocSetBuildResult:
    selected_candidates: tuple[PocSetCandidate, ...]
    selected_rows: tuple[dict[str, str], ...]
    summary: dict[str, object]


def build_poc_case_set(
    generated_cases_path: str | Path,
    template_cases_path: str | Path,
    *,
    total: int = 30,
    s1: int = 10,
    s2: int = 15,
    s3: int = 5,
    risk_profile: str = "customer_support",
    strict: bool = False,
    allow_fill: bool = False,
    warn_if_s1_missing: bool = False,
) -> PocSetBuildResult:
    if strict and allow_fill:
        raise ValueError("--strict and --allow-fill cannot be used together")
    if total <= 0:
        raise ValueError("total must be greater than 0")
    if min(s1, s2, s3) < 0:
        raise ValueError("severity quotas must be >= 0")
    if s1 + s2 + s3 > total:
        raise ValueError("s1 + s2 + s3 must not exceed total")

    profile_key = _resolve_risk_profile(risk_profile)
    domain_targets = _scaled_risk_targets(profile_key, total)
    source_targets = _planned_source_targets(profile_key, {"S1": s1, "S2": s2, "S3": s3})

    warnings: list[str] = []
    blocking_warnings: list[str] = []
    template_candidates = load_poc_candidates(template_cases_path, source_type="template")
    generated_candidates = load_poc_candidates(generated_cases_path, source_type="generated")
    candidates = _dedupe_candidates(template_candidates + generated_candidates)

    selected: list[PocSetCandidate] = []
    selected_ids: set[str] = set()
    remaining_risk_targets = dict(domain_targets)

    phase_plan = [
        ("S1", "template", source_targets["S1"].get("template", 0)),
        ("S1", "generated", source_targets["S1"].get("generated", 0)),
        ("S2", "generated", source_targets["S2"].get("generated", 0)),
        ("S2", "template", source_targets["S2"].get("template", 0)),
        ("S3", "generated", source_targets["S3"].get("generated", 0)),
    ]

    excluded_template_no_evidence: list[str] = []
    for band, source_type, quota in phase_plan:
        picks, excluded = _pick_candidates(
            candidates,
            selected_ids=selected_ids,
            remaining_risk_targets=remaining_risk_targets,
            count=quota,
            band=band,
            allowed_sources=[source_type],
            strict=strict,
            allow_fill=allow_fill,
        )
        excluded_template_no_evidence.extend(excluded)
        _append_selected(selected, selected_ids, remaining_risk_targets, picks)

    for band in ("S1", "S2", "S3"):
        remaining_band = {"S1": s1, "S2": s2, "S3": s3}[band] - _count_band(selected, band)
        if remaining_band <= 0:
            continue
        picks, excluded = _pick_candidates(
            candidates,
            selected_ids=selected_ids,
            remaining_risk_targets=remaining_risk_targets,
            count=remaining_band,
            band=band,
            allowed_sources=_DEFAULT_SOURCE_ORDER[band],
            strict=strict,
            allow_fill=allow_fill,
        )
        excluded_template_no_evidence.extend(excluded)
        _append_selected(selected, selected_ids, remaining_risk_targets, picks)

    if allow_fill and len(selected) < total:
        picks, excluded = _pick_candidates(
            candidates,
            selected_ids=selected_ids,
            remaining_risk_targets=remaining_risk_targets,
            count=total - len(selected),
            band=None,
            allowed_sources=["generated", "template"],
            strict=False,
            allow_fill=True,
        )
        excluded_template_no_evidence.extend(excluded)
        _append_selected(selected, selected_ids, remaining_risk_targets, picks)

    if excluded_template_no_evidence:
        warnings.append(
            "Excluded template cases without expected_evidence: "
            + ", ".join(sorted(set(excluded_template_no_evidence)))
        )

    actual_band_counts = {band: _count_band(selected, band) for band in ("S1", "S2", "S3")}
    if len(selected) < total:
        blocking_warnings.append(f"Requested total={total}, but selected only {len(selected)} cases.")
    for band, requested in {"S1": s1, "S2": s2, "S3": s3}.items():
        actual = actual_band_counts[band]
        if actual < requested:
            severity_label = "critical" if band == "S1" else "warning"
            blocking_warnings.append(
                f"{severity_label}: requested {requested} {band} cases, selected {actual}."
            )
    if warn_if_s1_missing and actual_band_counts["S1"] < s1:
        warnings.append(
            f"strong warning: S1 pool is short ({actual_band_counts['S1']}/{s1}); review templates or generated cases."
        )

    risk_shortfalls = [
        f"{domain}={remaining} short"
        for domain, remaining in remaining_risk_targets.items()
        if remaining > 0
    ]
    if risk_shortfalls:
        warnings.append("Risk-domain targets not fully met: " + ", ".join(risk_shortfalls))

    warnings = [*blocking_warnings, *warnings]
    if strict and blocking_warnings:
        raise ValueError("; ".join(blocking_warnings))

    selected_rows = tuple(candidate.output_row for candidate in selected)
    _validate_output_rows(selected_rows)
    summary = build_case_set_summary(selected, warnings)
    return PocSetBuildResult(
        selected_candidates=tuple(selected),
        selected_rows=selected_rows,
        summary=summary,
    )


def load_poc_candidates(path: str | Path, *, source_type: str) -> list[PocSetCandidate]:
    rows = load_csv_rows(path)
    candidates: list[PocSetCandidate] = []
    for row in rows:
        normalized = normalize_legacy_row(row)
        candidates.append(_row_to_candidate(normalized, source_type=source_type))
    return candidates


def build_case_set_summary(
    selected_candidates: list[PocSetCandidate], warnings: list[str]
) -> dict[str, object]:
    severity_mix = Counter(candidate.selection_band for candidate in selected_candidates)
    runtime_severity_mix = Counter(candidate.output_severity for candidate in selected_candidates)
    risk_domain_mix = Counter(candidate.risk_domain for candidate in selected_candidates)
    source_mix = Counter(candidate.source_type for candidate in selected_candidates)

    return {
        "total": len(selected_candidates),
        "severity_mix": {
            "S1": severity_mix.get("S1", 0),
            "S2": severity_mix.get("S2", 0),
            "S3": severity_mix.get("S3", 0),
        },
        "runtime_severity_mix": {
            "S1": runtime_severity_mix.get("S1", 0),
            "S2": runtime_severity_mix.get("S2", 0),
        },
        "runtime_severity_note": (
            "S3 is a PoC selection/classification band only. The runtime case schema "
            "continues to emit S1/S2 severities, so selected S3 candidates are written "
            "to cases.csv as severity=S2 with poc_band:S3 retained in notes."
        ),
        "runtime_severity_mapping": {
            "S1": "S1",
            "S2": "S2",
            "S3": "S2",
        },
        "risk_domain_mix": dict(sorted(risk_domain_mix.items())),
        "source_mix": {
            "template": source_mix.get("template", 0),
            "generated": source_mix.get("generated", 0),
        },
        "warnings": list(warnings),
    }


def write_poc_cases_csv(path: str | Path, rows: list[dict[str, str]] | tuple[dict[str, str], ...]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    extra_fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in POC_CASE_OUTPUT_FIELDS and key not in extra_fields:
                extra_fields.append(key)

    fieldnames = [*POC_CASE_OUTPUT_FIELDS, *sorted(extra_fields)]
    with open(output_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _stringify_csv_value(row.get(field, "")) for field in fieldnames})
    return output_path


def write_case_set_summary(path: str | Path, summary: dict[str, object]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def _resolve_risk_profile(risk_profile: str) -> str:
    key = _RISK_PROFILE_ALIASES.get(str(risk_profile or "").strip(), "")
    if not key:
        raise ValueError(f"Unsupported risk profile: {risk_profile}")
    return key


def _scaled_risk_targets(profile_key: str, total: int) -> dict[str, int]:
    base = _DEFAULT_RISK_TARGETS[profile_key]
    base_total = sum(base.values())
    if total == base_total:
        return dict(base)

    scaled: dict[str, int] = {}
    remainder: list[tuple[float, str]] = []
    allocated = 0
    for domain, count in base.items():
        raw = count * total / base_total
        integer = int(raw)
        scaled[domain] = integer
        allocated += integer
        remainder.append((raw - integer, domain))

    for _, domain in sorted(remainder, key=lambda item: (-item[0], item[1]))[: total - allocated]:
        scaled[domain] += 1
    return scaled


def _planned_source_targets(profile_key: str, band_targets: dict[str, int]) -> dict[str, dict[str, int]]:
    planned: dict[str, dict[str, int]] = {}
    for band, defaults in _DEFAULT_SOURCE_TARGETS[profile_key].items():
        remaining = band_targets.get(band, 0)
        planned[band] = {}
        for source_type, preferred_count in defaults:
            take = min(remaining, preferred_count)
            planned[band][source_type] = take
            remaining -= take
        if remaining > 0:
            for source_type in _DEFAULT_SOURCE_ORDER[band]:
                planned[band][source_type] = planned[band].get(source_type, 0) + remaining
                remaining = 0
                break
    return planned


def _row_to_candidate(row: dict[str, str], *, source_type: str) -> PocSetCandidate:
    notes = row.get("notes", "")
    metadata = _note_map(notes)
    selection_band = _selection_band(row.get("severity", "S2"), metadata)
    output_severity = _RUNTIME_SEVERITY[selection_band]
    risk_domain = _canonical_risk_domain(row.get("risk_domain") or row.get("category"))
    expected_evidence = tuple(_split_semicolon_list(row.get("expected_evidence", "")))
    expected_keywords = tuple(_split_semicolon_list(row.get("expected_keywords", "")))
    normalized_notes = _merge_notes(
        notes,
        source_type=source_type,
        selection_band=selection_band,
    )
    output_row = {
        **row,
        "name": row.get("name") or row.get("case_id", ""),
        "status": "active",
        "severity": output_severity,
        "eval_mode": row.get("eval_mode", "") or "evidence_keyword",
        "expected_answer": row.get("expected_answer", ""),
        "expected_evidence": ";".join(expected_evidence),
        "expected_keywords": ";".join(expected_keywords),
        "category": row.get("category", "") or "general",
        "risk_domain": risk_domain,
        "required_action": row.get("required_action", "") or _infer_required_action(output_severity),
        "evidence_required": _normalize_evidence_required(
            row.get("evidence_required", ""),
            expected_evidence=expected_evidence,
        ),
        "owner_role": row.get("owner_role", ""),
        "source_doc": row.get("source_doc", ""),
        "owner": row.get("owner", ""),
        "min_case_score": row.get("min_case_score", "") or ("100" if output_severity == "S1" else "85"),
        "updated_at": row.get("updated_at", "") or _today_iso(),
        "last_reviewed_at": row.get("last_reviewed_at", ""),
        "notes": normalized_notes,
    }
    return PocSetCandidate(
        case_id=row.get("case_id", ""),
        name=output_row["name"],
        question=row.get("question", ""),
        selection_band=selection_band,
        output_severity=output_severity,
        risk_domain=risk_domain,
        category=output_row["category"],
        source_type=source_type,
        expected_answer=output_row["expected_answer"],
        expected_evidence=expected_evidence,
        expected_keywords=expected_keywords,
        required_action=output_row["required_action"],
        notes=normalized_notes,
        question_signature=_question_signature(
            output_row["question"],
            expected_evidence,
            risk_domain,
        ),
        output_row=output_row,
    )


def _dedupe_candidates(candidates: list[PocSetCandidate]) -> list[PocSetCandidate]:
    grouped: dict[str, list[PocSetCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.question_signature, []).append(candidate)

    deduped: list[PocSetCandidate] = []
    for signature in sorted(grouped):
        grouped_candidates = grouped[signature]
        deduped.append(min(grouped_candidates, key=_dedupe_rank))
    return deduped


def _dedupe_rank(candidate: PocSetCandidate) -> tuple[int, int, int, int, str]:
    return (
        _BAND_ORDER[candidate.selection_band],
        _source_preference(candidate.selection_band, candidate.source_type),
        0 if candidate.expected_evidence else 1,
        _risk_domain_index(candidate.risk_domain),
        candidate.case_id,
    )


def _pick_candidates(
    candidates: list[PocSetCandidate],
    *,
    selected_ids: set[str],
    remaining_risk_targets: dict[str, int],
    count: int,
    band: str | None,
    allowed_sources: list[str],
    strict: bool,
    allow_fill: bool,
) -> tuple[list[PocSetCandidate], list[str]]:
    picks: list[PocSetCandidate] = []
    excluded_template_no_evidence: list[str] = []
    while len(picks) < count:
        available: list[PocSetCandidate] = []
        for candidate in candidates:
            if candidate.case_id in selected_ids:
                continue
            if band is not None and candidate.selection_band != band:
                continue
            if candidate.source_type not in allowed_sources:
                continue
            if not _candidate_allowed(candidate, strict=strict, allow_fill=allow_fill):
                if candidate.source_type == "template" and not candidate.expected_evidence:
                    excluded_template_no_evidence.append(candidate.case_id)
                continue
            available.append(candidate)
        if not available:
            break

        available.sort(
            key=lambda candidate: _selection_rank(
                candidate,
                remaining_risk_targets=remaining_risk_targets,
                allowed_sources=allowed_sources,
            )
        )
        picks.append(available[0])
        selected_ids.add(available[0].case_id)
    selected_ids.difference_update(candidate.case_id for candidate in picks)
    return picks, excluded_template_no_evidence


def _selection_rank(
    candidate: PocSetCandidate,
    *,
    remaining_risk_targets: dict[str, int],
    allowed_sources: list[str],
) -> tuple[int, int, int, str]:
    remaining = remaining_risk_targets.get(candidate.risk_domain, 0)
    source_rank = allowed_sources.index(candidate.source_type) if candidate.source_type in allowed_sources else len(allowed_sources)
    return (-remaining, source_rank, _risk_domain_index(candidate.risk_domain), candidate.case_id)


def _append_selected(
    selected: list[PocSetCandidate],
    selected_ids: set[str],
    remaining_risk_targets: dict[str, int],
    picks: list[PocSetCandidate],
) -> None:
    for candidate in picks:
        if candidate.case_id in selected_ids:
            continue
        selected.append(candidate)
        selected_ids.add(candidate.case_id)
        if candidate.risk_domain in remaining_risk_targets and remaining_risk_targets[candidate.risk_domain] > 0:
            remaining_risk_targets[candidate.risk_domain] -= 1


def _candidate_allowed(candidate: PocSetCandidate, *, strict: bool, allow_fill: bool) -> bool:
    if candidate.source_type != "template" or candidate.expected_evidence:
        return True
    if strict:
        return False
    if candidate.selection_band == "S1":
        return False
    return allow_fill or candidate.selection_band != "S1"


def _count_band(selected: list[PocSetCandidate], band: str) -> int:
    return sum(1 for candidate in selected if candidate.selection_band == band)


def _question_signature(question: str, expected_evidence: tuple[str, ...], risk_domain: str) -> str:
    normalized_question = " ".join(question.lower().split())
    normalized_evidence = "|".join(sorted({item.strip().lower() for item in expected_evidence if item.strip()}))
    return f"{risk_domain.lower()}||{normalized_question}||{normalized_evidence}"


def _selection_band(raw_severity: str, metadata: dict[str, str]) -> str:
    note_band = metadata.get("poc_band", "").strip().upper()
    if note_band in _BAND_ORDER:
        return note_band
    severity = str(raw_severity or "").strip().upper()
    if severity in _BAND_ORDER:
        return severity
    return "S2"


def _source_preference(band: str, source_type: str) -> int:
    if band == "S1":
        return 0 if source_type == "template" else 1
    return 0 if source_type == "generated" else 1


def _risk_domain_index(domain: str) -> int:
    ordered = list(_DEFAULT_RISK_TARGETS["customer_support"].keys())
    try:
        return ordered.index(domain)
    except ValueError:
        return len(ordered)


def _canonical_risk_domain(value: str | None) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return "general_faq"
    return _RISK_DOMAIN_ALIASES.get(raw, raw)


def _normalize_evidence_required(value: object, *, expected_evidence: tuple[str, ...]) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"true", "false"}:
        return normalized
    if normalized in {"1", "yes", "y", "required"}:
        return "true"
    return "true" if expected_evidence else "false"


def _infer_required_action(severity: str) -> str:
    return "block" if severity == "S1" else "allow_with_warning"


def _merge_notes(notes: str, *, source_type: str, selection_band: str) -> str:
    parts = _note_parts(notes)
    if not any(part.startswith("source_type:") for part in parts):
        parts.append(f"source_type:{source_type}")
    if not any(part.startswith("poc_band:") for part in parts):
        parts.append(f"poc_band:{selection_band}")
    return ";".join(parts)


def _note_map(notes: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for part in _note_parts(notes):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def _note_parts(notes: str) -> list[str]:
    return [part.strip() for part in str(notes or "").split(";") if part.strip()]


def _split_semicolon_list(raw: object) -> list[str]:
    values: list[str] = []
    for part in str(raw or "").split(";"):
        cleaned = part.strip()
        if cleaned and cleaned not in values:
            values.append(cleaned)
    return values


def _stringify_csv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _validate_output_rows(rows: tuple[dict[str, str], ...]) -> None:
    errors = validate_case_rows(list(rows))
    blocking = [error for error in errors if error.level == "error"]
    if blocking:
        messages = "; ".join(f"{error.case_id}:{error.field}:{error.message}" for error in blocking)
        raise ValueError(f"Generated cases.csv is invalid: {messages}")


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
