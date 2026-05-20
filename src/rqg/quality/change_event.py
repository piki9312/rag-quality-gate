"""Load and normalize change-event.yml inputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from rqg.domain import ChangeEvent
from rqg.quality.review_stage import normalize_review_stage


def load_change_event_file(path: str | Path | None) -> ChangeEvent | None:
    """Load a change-event YAML/JSON file and validate the input contract."""
    if path is None:
        return None
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None
    payload = _load_yaml_or_json(file_path)
    if not payload:
        return None
    normalized = _normalize_change_event_payload(payload)
    try:
        return ChangeEvent.model_validate(normalized)
    except ValidationError as exc:
        raise ValueError(f"Invalid change-event file: {exc}") from exc


def change_event_to_provenance(event: ChangeEvent) -> dict[str, Any]:
    """Return a provenance-compatible dict for existing report generation."""
    payload = event.model_dump(mode="json")
    payload["change_event_id"] = event.change_id
    return payload


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    return payload if isinstance(payload, dict) else {}


def _normalize_change_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "change_id": payload.get("change_id") or payload.get("change_event_id"),
        "change_type": payload.get("change_type", "unknown"),
        "change_summary": payload.get("change_summary") or payload.get("description") or "",
        "target_release": payload.get("target_release") or "",
        "changed_assets": payload.get("changed_assets") or [],
        "affected_documents": (
            payload.get("affected_documents") or payload.get("affected_sources") or []
        ),
        "affected_business_categories": payload.get("affected_business_categories") or [],
        "retest_reason": payload.get("retest_reason") or "",
        "review_stage": "",
    }
    if str(payload.get("review_stage") or "").strip():
        normalized["review_stage"] = normalize_review_stage(payload.get("review_stage"))
    normalized["changed_assets"] = [
        _normalize_changed_asset(item)
        for item in normalized.get("changed_assets", [])
        if isinstance(item, dict | str)
    ]
    for key in ("affected_documents", "affected_business_categories"):
        value = normalized.get(key)
        if isinstance(value, str) and value.strip():
            normalized[key] = [value.strip()]
        elif not isinstance(value, list):
            normalized[key] = []
    return normalized


def _normalize_changed_asset(item: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(item, str):
        return {"name": item}
    return dict(item)
