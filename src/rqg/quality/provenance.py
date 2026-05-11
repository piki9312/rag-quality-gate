"""Execution provenance helpers for eval/check/gate artifacts."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from rqg.cli.helpers import github_actions_enabled
from rqg.security import sanitize_error_message

SIMULATION_WARNING_EN = (
    "SIMULATION ONLY\n"
    "This result was produced in mock mode and must not be used as evidence of "
    "production RAG quality."
)
SIMULATION_WARNING_JA = (
    "本結果はmock / simulation実行によるものであり、" "実システム品質を証明するものではありません。"
)

logger = logging.getLogger(__name__)


def _safe_path_hint(path: Path) -> str:
    if not path.parts:
        return path.name or "<unknown>"
    return (
        "/".join(path.parts[-2:])
        if path.is_absolute() and len(path.parts) >= 2
        else path.as_posix()
    )


def _log_parse_failure(path: Path, exc: Exception) -> None:
    """Log parse failures with sanitized metadata only, never raw config content."""
    logger.warning(
        "Failed to parse config file path=%s error_type=%s error=%s",
        _safe_path_hint(path),
        type(exc).__name__,
        sanitize_error_message(exc),
    )


def determine_execution_mode(
    *,
    mock: bool,
    rag_endpoint: str | None = None,
    adapter_config_path: str | None = None,
    github_actions: bool | None = None,
) -> str:
    """Return a stable execution mode label for artifacts."""
    gh_actions = github_actions_enabled() if github_actions is None else github_actions
    external = bool((rag_endpoint or "").strip() or (adapter_config_path or "").strip())
    if mock and gh_actions:
        return "ci_mock"
    if mock:
        return "mock"
    if external:
        return "external_real"
    return "real"


def is_simulation_execution_mode(value: object) -> bool:
    return str(value or "").strip().lower() in {"mock", "ci_mock"}


def is_external_execution_mode(value: object) -> bool:
    return str(value or "").strip().lower() == "external_real"


def hash_text(value: str | None) -> str:
    normalized = value or ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def hash_file(path: str | Path | None) -> str | None:
    if path is None:
        return None
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def load_yaml_or_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return {}
    suffix = file_path.suffix.lower()
    try:
        text = file_path.read_text(encoding="utf-8")
        if suffix == ".json":
            payload = json.loads(text)
        else:
            payload = yaml.safe_load(text)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        _log_parse_failure(file_path, exc)
        return {}
    return payload if isinstance(payload, dict) else {}


def infer_doc_snapshot_ids(index_dir: str | Path | None) -> list[str]:
    if index_dir is None:
        return []
    snapshot_dir = Path(index_dir) / "snapshots"
    if not snapshot_dir.exists() or not snapshot_dir.is_dir():
        return []
    snapshot_ids: list[str] = []
    for file_path in sorted(snapshot_dir.glob("*.json")):
        payload = load_yaml_or_json(file_path)
        snapshot_id = str(payload.get("snapshot_id") or "").strip()
        if snapshot_id:
            snapshot_ids.append(snapshot_id)
    return snapshot_ids


def infer_index_version(index_dir: str | Path | None) -> str | None:
    snapshot_ids = infer_doc_snapshot_ids(index_dir)
    if not snapshot_ids:
        return None
    return hash_text("|".join(snapshot_ids))


def quality_pack_version(quality_pack_path: str | Path | None) -> str | None:
    payload = load_yaml_or_json(quality_pack_path)
    if not payload:
        return None
    pack = payload.get("pack", {})
    if not isinstance(pack, dict):
        return None
    return str(pack.get("pack_version") or pack.get("version") or "").strip() or None


def case_set_version(cases_path: str | Path | None) -> str | None:
    return hash_file(cases_path)


def load_change_event(path: str | Path | None) -> dict[str, Any] | None:
    payload = load_yaml_or_json(path)
    if not payload:
        return None
    normalized = {
        "change_event_id": str(payload.get("change_event_id") or "").strip() or None,
        "change_type": str(payload.get("change_type") or "unknown").strip() or "unknown",
        "description": str(payload.get("description") or "").strip(),
        "changed_by": str(payload.get("changed_by") or "").strip(),
        "changed_at": str(payload.get("changed_at") or "").strip(),
        "affected_sources": (
            payload.get("affected_sources")
            if isinstance(payload.get("affected_sources"), list)
            else []
        ),
        "linked_run_ids": (
            payload.get("linked_run_ids") if isinstance(payload.get("linked_run_ids"), list) else []
        ),
    }
    if not normalized["change_event_id"]:
        return None
    return normalized


def load_manual_review_records(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return []
    try:
        text = file_path.read_text(encoding="utf-8")
        payload = json.loads(text) if file_path.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, ValueError, yaml.YAMLError):
        return []
    rows = payload.get("reviews", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        review_id = str(item.get("review_id") or "").strip()
        if not review_id:
            continue
        normalized.append(
            {
                "review_id": review_id,
                "case_id": str(item.get("case_id") or "").strip(),
                "run_id": str(item.get("run_id") or "").strip(),
                "reviewer": str(item.get("reviewer") or "").strip(),
                "review_status": str(item.get("review_status") or "").strip() or "needs_followup",
                "review_comment": str(item.get("review_comment") or "").strip(),
                "reviewed_at": str(item.get("reviewed_at") or "").strip(),
                "evidence_checked": bool(item.get("evidence_checked")),
                "approval_scope": str(item.get("approval_scope") or "").strip(),
                "expires_at": str(item.get("expires_at") or "").strip() or None,
            }
        )
    return normalized


def build_run_provenance(
    *,
    run_id: str,
    execution_mode: str,
    report_mode: str,
    model_name: str | None,
    prompt_hash: str | None,
    prompt_version: str | None,
    retrieval_config_hash: str | None,
    adapter_config_hash: str | None,
    doc_snapshot_ids: list[str] | None = None,
    index_version: str | None = None,
    quality_pack_version_value: str | None = None,
    case_set_version_value: str | None = None,
    change_event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "execution_mode": execution_mode,
        "report_mode": report_mode,
        "model": model_name,
        "prompt_hash": prompt_hash,
        "prompt_version": prompt_version,
        "retrieval_config_hash": retrieval_config_hash,
        "adapter_config_hash": adapter_config_hash,
        "doc_snapshot_ids": list(doc_snapshot_ids or []),
        "index_version": index_version,
        "quality_pack_version": quality_pack_version_value,
        "case_set_version": case_set_version_value,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "change_event": change_event,
        "change_event_id": (change_event or {}).get("change_event_id"),
    }


def write_run_provenance(log_dir: str | Path, run_id: str, payload: dict[str, Any]) -> Path:
    output_path = Path(log_dir) / f"run-provenance-{run_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    latest_path = output_path.parent / "run-provenance-latest.json"
    latest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def load_run_provenance(log_dir: str | Path, run_id: str | None) -> dict[str, Any]:
    if not run_id:
        return {}
    file_path = Path(log_dir) / f"run-provenance-{run_id}.json"
    return load_yaml_or_json(file_path)


def append_simulation_warning(lines: list[str], execution_mode: str) -> None:
    if not is_simulation_execution_mode(execution_mode):
        return
    if SIMULATION_WARNING_EN in lines or SIMULATION_WARNING_JA in lines:
        return
    if "## Simulation Warning" not in lines:
        lines.extend(["## Simulation Warning", ""])
    lines.extend(
        [
            SIMULATION_WARNING_EN,
            "",
            SIMULATION_WARNING_JA,
            "",
        ]
    )
