"""Load Case Intent Library YAML assets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from rqg.case_assets.intent_schema import CaseIntent, CaseIntentLibraryError


def load_case_intents(path: str | Path) -> list[CaseIntent]:
    """Load Case Intent YAML files from a file or directory."""
    root = Path(path)
    files = _discover_yaml_files(root)
    intents: list[CaseIntent] = []
    seen: dict[str, Path] = {}

    for file_path in files:
        payload = _read_yaml_mapping(file_path)
        intent = _validate_intent_payload(file_path, payload)
        existing_path = seen.get(intent.intent_id)
        if existing_path is not None:
            raise CaseIntentLibraryError(
                "Duplicate Case Intent id "
                f"'{intent.intent_id}' in {file_path} "
                f"(already defined in {existing_path})"
            )
        seen[intent.intent_id] = file_path
        intents.append(intent)

    return intents


def _discover_yaml_files(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() not in {".yml", ".yaml"}:
            raise CaseIntentLibraryError(f"Case Intent path is not YAML: {path}")
        return [path]
    if path.is_dir():
        files = [
            candidate
            for candidate in path.rglob("*")
            if candidate.is_file() and candidate.suffix.lower() in {".yml", ".yaml"}
        ]
        return sorted(files, key=lambda item: item.as_posix())
    raise CaseIntentLibraryError(f"Case Intent path does not exist: {path}")


def _read_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CaseIntentLibraryError(f"Failed to read Case Intent YAML {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CaseIntentLibraryError(f"Case Intent YAML must be a mapping: {path}")
    return payload


def _validate_intent_payload(path: Path, payload: dict[str, Any]) -> CaseIntent:
    intent_id = str(payload.get("intent_id") or "<unknown>")
    try:
        return CaseIntent.model_validate(payload)
    except ValidationError as exc:
        raise CaseIntentLibraryError(
            f"Invalid Case Intent in {path} intent_id={intent_id}: {exc}"
        ) from exc
    except ValueError as exc:
        raise CaseIntentLibraryError(
            f"Invalid Case Intent in {path} intent_id={intent_id}: {exc}"
        ) from exc
