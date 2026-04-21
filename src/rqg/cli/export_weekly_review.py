"""rqg export-weekly-review sub-command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..quality.weekly_review import (
    DEFAULT_WEEKLY_REVIEW_LABELS,
    build_weekly_review_issue_payload,
)
from .helpers import write_json_data_output


def cmd_export_weekly_review(args: argparse.Namespace) -> int:
    """Export a GitHub issue payload from gate-history-summary.json."""
    summary_path = (
        Path(args.summary_file)
        if args.summary_file
        else Path(args.log_dir) / "gate-history-summary.json"
    )
    if not summary_path.exists():
        print(f"No gate history summary found at {summary_path}")
        return 1

    try:
        summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Failed to parse {summary_path}: {exc}")
        return 1

    labels = args.label or list(DEFAULT_WEEKLY_REVIEW_LABELS)
    issue_payload = build_weekly_review_issue_payload(
        summary_payload,
        week_start=args.week_start,
        title_prefix=args.title_prefix,
        title_suffix=args.title_suffix,
        labels=labels,
    )

    output_path = (
        Path(args.output)
        if args.output
        else summary_path.with_name("weekly-review-issue.json")
    )
    saved_path = write_json_data_output(output_path, issue_payload)
    print(f"Saved weekly review issue payload to {saved_path}")
    return 0