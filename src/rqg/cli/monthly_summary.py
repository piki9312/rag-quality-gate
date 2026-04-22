"""rqg monthly-summary sub-command."""

from __future__ import annotations

import argparse
from pathlib import Path

from .helpers import write_json_data_output, write_text_output


def cmd_monthly_summary(args: argparse.Namespace) -> int:
    from ..quality.history import load_gate_decision_history
    from ..quality.monthly_summary import (
        build_monthly_summary_payload,
        render_monthly_summary_markdown,
    )

    history_path = Path(args.log_dir) / "gate-decisions.jsonl"
    decisions = load_gate_decision_history(history_path)
    summary = build_monthly_summary_payload(decisions, month=args.month)
    markdown = render_monthly_summary_markdown(summary)
    print(markdown, end="")

    markdown_output = (
        Path(args.markdown_output)
        if args.markdown_output
        else Path(args.log_dir) / "monthly-summary.md"
    )
    json_output = (
        Path(args.json_output) if args.json_output else Path(args.log_dir) / "monthly-summary.json"
    )
    saved_markdown = write_text_output(markdown_output, markdown)
    saved_json = write_json_data_output(json_output, summary)
    print(f"Saved monthly summary markdown to {saved_markdown}")
    print(f"Saved monthly summary JSON to {saved_json}")
    return 0 if summary.get("total_runs", 0) else 1
