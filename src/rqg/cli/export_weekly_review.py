"""rqg export-weekly-review sub-command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ..quality.weekly_review import (
    DEFAULT_WEEKLY_REVIEW_LABELS,
    build_weekly_review_issue_payload,
)
from .helpers import write_json_data_output


def cmd_export_weekly_review(args: argparse.Namespace) -> int:
    """Export a GitHub issue payload from gate-history-summary.json or gate-report.json."""
    resolved = _load_weekly_review_source(args)
    if resolved is None:
        return 1

    summary_payload, source_path = resolved

    labels = args.label or list(DEFAULT_WEEKLY_REVIEW_LABELS)
    issue_payload = build_weekly_review_issue_payload(
        summary_payload,
        week_start=args.week_start,
        title_prefix=args.title_prefix,
        title_suffix=args.title_suffix,
        labels=labels,
    )

    output_path = (
        Path(args.output) if args.output else source_path.with_name("weekly-review-issue.json")
    )
    saved_path = write_json_data_output(output_path, issue_payload)
    print(f"Saved weekly review issue payload to {saved_path}")
    return 0


def _load_weekly_review_source(args: argparse.Namespace) -> tuple[dict[str, Any], Path] | None:
    if getattr(args, "bundle_file", None):
        bundle_path = Path(args.bundle_file)
        payload = _read_json_payload(bundle_path, missing_label="gate report bundle")
        if payload is None:
            return None
        summary_payload = _extract_history_summary(
            payload, source_path=bundle_path, require_bundle=True
        )
        if summary_payload is None:
            return None
        return summary_payload, bundle_path

    summary_path = (
        Path(args.summary_file)
        if args.summary_file
        else Path(args.log_dir) / "gate-history-summary.json"
    )
    payload = _read_json_payload(summary_path, missing_label="gate history summary")
    if payload is None:
        return None

    summary_payload = _extract_history_summary(
        payload, source_path=summary_path, require_bundle=False
    )
    if summary_payload is None:
        return None
    return summary_payload, summary_path


def _read_json_payload(path: Path, *, missing_label: str) -> dict[str, Any] | None:
    if not path.exists():
        print(f"No {missing_label} found at {path}")
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Failed to parse {path}: {exc}")
        return None

    if not isinstance(payload, dict):
        print(f"[ERROR] Expected JSON object at {path}")
        return None
    return payload


def _extract_history_summary(
    payload: dict[str, Any],
    *,
    source_path: Path,
    require_bundle: bool,
) -> dict[str, Any] | None:
    summary_payload = payload.get("history_summary")
    if isinstance(summary_payload, dict):
        return summary_payload

    if require_bundle:
        print(f"[ERROR] Bundle file does not contain history_summary: {source_path}")
        return None

    return payload
