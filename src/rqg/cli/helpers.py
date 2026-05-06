"""rqg.cli — shared helpers used by every sub-command module."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..domain import DocumentSnapshot

# ---------------------------------------------------------------------------
# JSON / JSONL output helpers
# ---------------------------------------------------------------------------


def write_json_output(path: str | Path, model: object) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def write_json_data_output(path: str | Path, payload: Any) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def write_json_list_output(path: str | Path, models: list[object]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [model.model_dump(mode="json") for model in models]
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def append_jsonl_output(path: str | Path, model: object) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(model.model_dump_json() + "\n")
    return output_path


def write_text_output(path: str | Path, content: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def github_actions_enabled() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"


def github_actions_data_boundary_guidance() -> str:
    return (
        "GitHub Actions may handle sample/mock/dummy data only; customer/full/external runs "
        "must be executed locally, on a private runner, or in a customer-controlled environment."
    )


def github_actions_fail_fast_message(reason: str) -> str:
    return f"[ERROR] {reason} {github_actions_data_boundary_guidance()}"


# ---------------------------------------------------------------------------
# Log-dir / index-dir utilities
# ---------------------------------------------------------------------------


def reset_eval_log_dir(log_dir: str | Path) -> list[Path]:
    """Remove eval/check artifacts from a log_dir to make runs reproducible."""
    path = Path(log_dir)
    if not path.exists():
        return []

    removed: list[Path] = []

    for jsonl_path in sorted(path.glob("*.jsonl")):
        if len(jsonl_path.stem) == 8 and jsonl_path.stem.isdigit():
            jsonl_path.unlink(missing_ok=True)
            removed.append(jsonl_path)

    for filename in (
        "gate-report.md",
        "gate-report.json",
        "gate-decision.json",
        "gate-decisions.jsonl",
        "gate-history-summary.json",
    ):
        artifact_path = path / filename
        if artifact_path.exists() and artifact_path.is_file():
            artifact_path.unlink(missing_ok=True)
            removed.append(artifact_path)

    dry_run_dir = path / "dry-run"
    if dry_run_dir.exists() and dry_run_dir.is_dir():
        shutil.rmtree(dry_run_dir, ignore_errors=True)
        removed.append(dry_run_dir)

    return removed


def build_dry_run_log_dir(log_dir: str | Path) -> Path:
    """Return an isolated artifact directory for a gate dry run."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_token = uuid.uuid4().hex[:8]
    return Path(log_dir) / "dry-run" / f"{stamp}-{run_token}"


def index_dir_is_under_runs(index_dir: str | Path) -> bool:
    """Return True if index_dir resolves to workspace runs/ (or relative runs/*)."""
    path = Path(index_dir)

    if path.is_absolute():
        runs_root = (Path.cwd() / "runs").resolve()
        try:
            path.resolve().relative_to(runs_root)
            return True
        except ValueError:
            return False

    if not path.parts:
        return False
    return path.parts[0].lower() == "runs"


def validate_index_dir(index_dir: str | Path) -> bool:
    """Reject index dirs under runs/ to keep eval artifacts and index artifacts separated."""
    import sys

    if index_dir_is_under_runs(index_dir):
        print(
            "[ERROR] --index-dir must be outside runs/ (e.g. 'index' or '.cache/rqg-index').",
            file=sys.stderr,
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------


def load_snapshot_from_file(path: str | Path) -> DocumentSnapshot:
    snapshot_path = Path(path)
    return DocumentSnapshot.model_validate_json(snapshot_path.read_text(encoding="utf-8"))


def build_document_snapshot(
    *,
    source_path: Path,
    text: str,
    version: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> DocumentSnapshot:
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    snapshot_id = f"{source_path.stem}-{content_hash[:12]}"
    return DocumentSnapshot(
        snapshot_id=snapshot_id,
        doc_id=source_path.as_posix(),
        title=source_path.stem,
        source_path=source_path.as_posix(),
        content_hash=content_hash,
        created_at=datetime.now(timezone.utc),
        version=version,
        metadata=metadata or {},
    )


def snapshot_output_path(index_dir: str | Path, snapshot: DocumentSnapshot) -> Path:
    return Path(index_dir) / "snapshots" / f"{snapshot.snapshot_id}.json"


# ---------------------------------------------------------------------------
# Pack / profile helpers
# ---------------------------------------------------------------------------


def pack_profile_templates() -> dict[str, tuple[Path, str]]:
    root_dir = Path(__file__).resolve().parents[3]
    return {
        "demo_cycle": (
            root_dir / "templates" / "sample_pack",
            "Demo cycle starter pack template",
        ),
        "hr": (
            root_dir / "packs" / "hr",
            "HR internal-documents profile",
        ),
        "wiki": (
            root_dir / "packs" / "wiki",
            "Wiki/FAQ internal-documents profile",
        ),
        "customer_support": (
            root_dir / "packs" / "customer_support_pack",
            "Customer support FAQ Proof Gate profile",
        ),
    }


PACK_PROFILE_ALIASES: dict[str, str] = {
    "sample": "demo_cycle",
    "customer_support_pack": "customer_support",
}


def normalize_pack_profile(profile: str) -> str:
    return PACK_PROFILE_ALIASES.get(profile, profile)


def resolve_pack_template_dir(profile: str) -> Path:
    normalized_profile = normalize_pack_profile(profile)
    template_by_profile = {
        profile_name: template_path
        for profile_name, (template_path, _) in pack_profile_templates().items()
    }

    template_dir = template_by_profile[normalized_profile]
    if template_dir.exists():
        return template_dir
    raise FileNotFoundError(
        "Pack template not found for profile "
        f"'{profile}' (resolved to '{normalized_profile}'): {template_dir}"
    )


# ---------------------------------------------------------------------------
# Validation error formatting
# ---------------------------------------------------------------------------


def format_validation_errors(
    errors: list,
) -> tuple[list[str], list[str]]:
    """Split validation errors into error/warn message lists."""
    err_msgs: list[str] = []
    warn_msgs: list[str] = []
    for e in errors:
        tag = "ERROR" if e.level == "error" else "WARN"
        msg = f"[{tag}] {e.case_id} / {e.field}: {e.message}"
        if e.level == "error":
            err_msgs.append(msg)
        else:
            warn_msgs.append(msg)
    return err_msgs, warn_msgs
