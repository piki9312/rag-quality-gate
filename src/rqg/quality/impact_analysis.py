"""Impact analysis utilities for snapshot updates."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from rqg.casegen.sections import extract_sections_from_snapshot
from rqg.domain import DocumentSnapshot, EvalCase, ImpactDetail, ImpactReport
from rqg.presentation.markdown import render_impact_report_review_markdown
from rqg.quality.loader import load_eval_cases


LEGACY_EVIDENCE_COMPAT_START = date(2026, 3, 27)
LEGACY_EVIDENCE_COMPAT_UNTIL = date(2026, 6, 30)


def _section_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _normalize_evidence_ref(value: str) -> str:
    return value.strip().replace("\\", "/")


def _split_evidence_id(evidence_id: str) -> tuple[str, str]:
    normalized = _normalize_evidence_ref(evidence_id)
    if "#" not in normalized:
        return normalized, ""
    prefix, fragment = normalized.split("#", 1)
    return prefix, fragment


def _build_doc_aliases(old_snapshot: DocumentSnapshot, new_snapshot: DocumentSnapshot) -> set[str]:
    aliases = {
        _normalize_evidence_ref(old_snapshot.doc_id),
        _normalize_evidence_ref(new_snapshot.doc_id),
        _normalize_evidence_ref(old_snapshot.source_path),
        _normalize_evidence_ref(new_snapshot.source_path),
    }
    return {alias for alias in aliases if alias}


def _build_legacy_compatible_changed_ids(
    changed_evidence_ids: list[str],
    old_snapshot: DocumentSnapshot,
    new_snapshot: DocumentSnapshot,
) -> set[str]:
    aliases = _build_doc_aliases(old_snapshot, new_snapshot)
    compatible_ids = {_normalize_evidence_ref(evidence_id) for evidence_id in changed_evidence_ids}
    for evidence_id in changed_evidence_ids:
        _, fragment = _split_evidence_id(evidence_id)
        if not fragment:
            continue
        for alias in aliases:
            compatible_ids.add(f"{alias}#{fragment}")
    return compatible_ids


def _is_legacy_compat_active(reference_date: date | None = None) -> bool:
    current = reference_date or datetime.now(timezone.utc).date()
    return LEGACY_EVIDENCE_COMPAT_START <= current <= LEGACY_EVIDENCE_COMPAT_UNTIL


def _extract_section_hashes(
    snapshot: DocumentSnapshot,
    *,
    snapshot_path: str | Path | None = None,
) -> dict[str, str]:
    try:
        sections = extract_sections_from_snapshot(snapshot, snapshot_path=snapshot_path)
    except Exception as exc:  # pragma: no cover - branch covered by error tests
        raise ValueError(
            f"Failed to extract sections from snapshot '{snapshot.snapshot_id}': {exc}"
        ) from exc

    hashes: dict[str, str] = {}
    for section in sections:
        normalized = f"{section.heading}\n{section.content}".strip()
        hashes[section.section_id] = _section_hash(normalized)
    return hashes


def detect_changed_evidence_ids(
    old_snapshot: DocumentSnapshot,
    new_snapshot: DocumentSnapshot,
    *,
    old_snapshot_path: str | Path | None = None,
    new_snapshot_path: str | Path | None = None,
) -> list[str]:
    """Detect changed section-level evidence IDs between two snapshots."""
    old_hashes = _extract_section_hashes(old_snapshot, snapshot_path=old_snapshot_path)
    new_hashes = _extract_section_hashes(new_snapshot, snapshot_path=new_snapshot_path)

    changed_ids: list[str] = []
    for evidence_id in sorted(set(old_hashes) | set(new_hashes)):
        if old_hashes.get(evidence_id) != new_hashes.get(evidence_id):
            changed_ids.append(evidence_id)
    return changed_ids


def extract_impacted_cases(
    cases: list[EvalCase],
    changed_evidence_ids: list[str],
    *,
    compatible_changed_evidence_ids: set[str] | None = None,
) -> tuple[list[str], list[ImpactDetail], int]:
    """Extract impacted case IDs based on expected_evidence overlap."""
    if not changed_evidence_ids:
        return [], [], 0

    changed_set = {_normalize_evidence_ref(evidence_id) for evidence_id in changed_evidence_ids}
    if compatible_changed_evidence_ids is None:
        compatible_set = changed_set
    else:
        compatible_set = {_normalize_evidence_ref(evidence_id) for evidence_id in compatible_changed_evidence_ids}
    legacy_only_set = compatible_set - changed_set

    impacted_case_ids: list[str] = []
    details: list[ImpactDetail] = []
    legacy_match_count = 0

    for case in cases:
        matched: list[tuple[str, str]] = []
        for evidence_id in case.expected_evidence:
            normalized_evidence_id = _normalize_evidence_ref(evidence_id)
            if normalized_evidence_id not in compatible_set:
                continue
            if normalized_evidence_id in legacy_only_set:
                matched.append((evidence_id, "legacy_compat"))
                legacy_match_count += 1
            else:
                matched.append((evidence_id, "strict"))
        if not matched:
            continue
        impacted_case_ids.append(case.case_id)
        for evidence_id, match_mode in matched:
            details.append(
                ImpactDetail(
                    case_id=case.case_id,
                    matched_evidence_id=evidence_id,
                    question=case.question,
                    match_mode=match_mode,
                )
            )

    return impacted_case_ids, details, legacy_match_count


def build_impact_report(
    old_snapshot: DocumentSnapshot,
    new_snapshot: DocumentSnapshot,
    cases: list[EvalCase],
    *,
    old_snapshot_path: str | Path | None = None,
    new_snapshot_path: str | Path | None = None,
    reference_date: date | None = None,
) -> ImpactReport:
    """Build an impact report from snapshots and eval cases."""
    changed_evidence_ids = detect_changed_evidence_ids(
        old_snapshot,
        new_snapshot,
        old_snapshot_path=old_snapshot_path,
        new_snapshot_path=new_snapshot_path,
    )
    legacy_compatibility_active = _is_legacy_compat_active(reference_date)
    if legacy_compatibility_active:
        compatible_changed_ids = _build_legacy_compatible_changed_ids(
            changed_evidence_ids,
            old_snapshot,
            new_snapshot,
        )
    else:
        compatible_changed_ids = {_normalize_evidence_ref(evidence_id) for evidence_id in changed_evidence_ids}
    impacted_case_ids, details, legacy_match_count = extract_impacted_cases(
        cases,
        changed_evidence_ids,
        compatible_changed_evidence_ids=compatible_changed_ids,
    )

    return ImpactReport(
        old_snapshot_id=old_snapshot.snapshot_id,
        new_snapshot_id=new_snapshot.snapshot_id,
        changed_evidence_ids=changed_evidence_ids,
        impacted_case_ids=impacted_case_ids,
        details=details,
        legacy_match_count=legacy_match_count,
        legacy_compatibility_active=legacy_compatibility_active,
        created_at=datetime.now(timezone.utc),
    )


def load_eval_cases_from_path(path: str | Path) -> list[EvalCase]:
    """Load EvalCase list from JSON or CSV."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Cases file not found: {file_path}")

    if file_path.suffix.lower() == ".csv":
        try:
            return load_eval_cases(str(file_path))
        except ValidationError as exc:
            raise ValueError(f"Invalid case row in CSV: {exc}") from exc
        except csv.Error as exc:
            raise ValueError(f"Invalid CSV format: {exc}") from exc

    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Cases JSON parse error: {exc}") from exc

    rows: list[object]
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        rows = payload["cases"]
    elif isinstance(payload, dict):
        rows = [payload]
    else:
        raise ValueError("Cases JSON must be a list, a single object, or an object with 'cases'.")

    cases: list[EvalCase] = []
    for row in rows:
        try:
            cases.append(EvalCase.model_validate(row))
        except ValidationError as exc:
            raise ValueError(f"Invalid EvalCase in cases file: {exc}") from exc
    return cases


def render_impact_review_text(report: ImpactReport) -> str:
    """Render impact report in review-friendly Markdown."""
    return render_impact_report_review_markdown(report)


def write_impact_review(path: str | Path, report: ImpactReport) -> Path:
    """Write impact review output (.md)."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()
    if suffix != ".md":
        raise ValueError("Impact review output must use .md")

    output_path.write_text(render_impact_review_text(report), encoding="utf-8")
    return output_path
