"""rqg history sub-command."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..quality.history import (
    filter_gate_decision_history,
    load_gate_decision_history,
    render_gate_history_markdown,
)


def cmd_history(args: argparse.Namespace) -> int:
    """Render recent gate decision history from append-only JSONL."""
    history_path = Path(args.log_dir) / "gate-decisions.jsonl"
    decisions = load_gate_decision_history(history_path)
    decisions = filter_gate_decision_history(
        decisions,
        status=getattr(args, "status", None),
        last=getattr(args, "last", None),
    )
    if not decisions:
        print(f"No gate decision history found in {history_path}")
        return 1

    md = render_gate_history_markdown(decisions)
    print(md)

    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(md, encoding="utf-8")
        print(f"Saved history report to {output_path}")

    return 0
