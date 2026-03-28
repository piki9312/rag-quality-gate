"""Helpers to migrate legacy expected_evidence references to doc_id format."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pydantic import ValidationError

from rqg.domain import DocumentSnapshot, EvalCase
from rqg.quality.loader import load_eval_cases


def _normalize_evidence_ref(value: str) -> str:
    return value.strip().replace("\\", "/")


def _split_evidence_id(evidence_id: str) -> tuple[str, str]:
    normalized = _normalize_evidence_ref(evidence_id)
    if "#" not in normalized:
        return normalized, ""
    prefix, fragment = normalized.split("#", 1)
    return prefix, fragment


def _load_snapshot(path: str | Path) -> DocumentSnapshot:
    snapshot_path = Path(path)
    return DocumentSnapshot.model_validate_json(snapshot_path.read_text(encoding="utf-8"))


def _collect_snapshot_paths(snapshot_paths: list[str], snapshot_dir: str | None) -> list[Path]:
    collected = [Path(path) for path in snapshot_paths]
    if snapshot_dir:
        base_dir = Path(snapshot_dir)
        if not base_dir.exists():
            raise FileNotFoundError(f"Snapshot directory not found: {base_dir}")
        for candidate in sorted(base_dir.rglob("*.json")):
            collected.append(candidate)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in collected:
        normalized = path.resolve().as_posix() if path.exists() else path.as_posix()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(path)
    return unique


def load_snapshots(
    snapshot_paths: list[str], snapshot_dir: str | None = None
) -> list[DocumentSnapshot]:
    snapshots: list[DocumentSnapshot] = []
    for path in _collect_snapshot_paths(snapshot_paths, snapshot_dir):
        snapshots.append(_load_snapshot(path))
    return snapshots


def _build_source_to_doc_id_map(snapshots: list[DocumentSnapshot]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for snapshot in snapshots:
        source_key = _normalize_evidence_ref(snapshot.source_path)
        doc_id = _normalize_evidence_ref(snapshot.doc_id)
        if not source_key or not doc_id:
            continue
        mapping[source_key] = doc_id
        mapping[source_key.lower()] = doc_id

        source_path = Path(snapshot.source_path)
        if source_path.exists():
            resolved = _normalize_evidence_ref(source_path.resolve().as_posix())
            mapping[resolved] = doc_id
            mapping[resolved.lower()] = doc_id

    return mapping


def _looks_like_path_reference(prefix: str) -> bool:
    return "/" in prefix or "\\" in prefix or ":" in prefix


def _convert_evidence_id(
    evidence_id: str,
    mapping: dict[str, str],
    known_doc_ids: set[str],
) -> tuple[str, bool, bool]:
    prefix, fragment = _split_evidence_id(evidence_id)
    mapped_doc_id = mapping.get(prefix) or mapping.get(prefix.lower())
    if not mapped_doc_id:
        unresolved = _looks_like_path_reference(prefix) and prefix not in known_doc_ids
        return _normalize_evidence_ref(evidence_id), False, unresolved

    converted = mapped_doc_id if not fragment else f"{mapped_doc_id}#{fragment}"
    return converted, True, False


def load_cases_with_format(path: str | Path) -> tuple[list[EvalCase], str]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Cases file not found: {file_path}")

    if file_path.suffix.lower() == ".csv":
        try:
            return load_eval_cases(str(file_path)), "csv"
        except ValidationError as exc:
            raise ValueError(f"Invalid case row in CSV: {exc}") from exc
        except csv.Error as exc:
            raise ValueError(f"Invalid CSV format: {exc}") from exc

    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Cases JSON parse error: {exc}") from exc

    rows: list[object]
    payload_format: str
    if isinstance(payload, list):
        rows = payload
        payload_format = "json-list"
    elif isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        rows = payload["cases"]
        payload_format = "json-cases"
    elif isinstance(payload, dict):
        rows = [payload]
        payload_format = "json-object"
    else:
        raise ValueError("Cases JSON must be a list, a single object, or an object with 'cases'.")

    cases: list[EvalCase] = []
    for row in rows:
        try:
            cases.append(EvalCase.model_validate(row))
        except ValidationError as exc:
            raise ValueError(f"Invalid EvalCase in cases file: {exc}") from exc
    return cases, payload_format


def migrate_expected_evidence(
    cases: list[EvalCase], snapshots: list[DocumentSnapshot]
) -> tuple[list[EvalCase], dict[str, int]]:
    mapping = _build_source_to_doc_id_map(snapshots)
    known_doc_ids = {_normalize_evidence_ref(snapshot.doc_id) for snapshot in snapshots}
    migrated_cases: list[EvalCase] = []

    total_refs = 0
    converted_refs = 0
    unresolved_refs = 0
    converted_case_count = 0

    for case in cases:
        migrated_evidence: list[str] = []
        case_changed = False
        for evidence_id in case.expected_evidence:
            total_refs += 1
            converted_id, converted, unresolved = _convert_evidence_id(
                evidence_id,
                mapping,
                known_doc_ids,
            )
            if converted:
                converted_refs += 1
                case_changed = True
            if unresolved:
                unresolved_refs += 1
            migrated_evidence.append(converted_id)

        migrated_cases.append(case.model_copy(update={"expected_evidence": migrated_evidence}))
        if case_changed:
            converted_case_count += 1

    stats = {
        "total_cases": len(cases),
        "converted_case_count": converted_case_count,
        "total_evidence_refs": total_refs,
        "converted_evidence_refs": converted_refs,
        "unresolved_legacy_refs": unresolved_refs,
    }
    return migrated_cases, stats


def write_cases_with_format(path: str | Path, cases: list[EvalCase], payload_format: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".csv":
        with open(output_path, "w", newline="", encoding="utf-8") as file_obj:
            writer = csv.DictWriter(
                file_obj,
                fieldnames=[
                    "case_id",
                    "question",
                    "expected_evidence",
                    "expected_keywords",
                    "risk_level",
                    "doc_snapshot_id",
                    "notes",
                ],
            )
            writer.writeheader()
            for case in cases:
                writer.writerow(
                    {
                        "case_id": case.case_id,
                        "question": case.question,
                        "expected_evidence": ";".join(case.expected_evidence),
                        "expected_keywords": ";".join(case.expected_keywords),
                        "risk_level": case.risk_level,
                        "doc_snapshot_id": case.doc_snapshot_id,
                        "notes": case.notes or "",
                    }
                )
        return output_path

    if output_path.suffix.lower() == ".json":
        case_payload = [case.model_dump(mode="json") for case in cases]
        if payload_format == "json-object":
            payload: object = case_payload[0] if case_payload else {}
        elif payload_format == "json-cases":
            payload = {"cases": case_payload}
        else:
            payload = case_payload

        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path

    raise ValueError("Output must use .json or .csv")
