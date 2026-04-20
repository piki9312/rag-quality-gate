"""Gate decision history helpers."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from ..domain import GateDecision


def load_gate_decision_history(path: str | Path) -> list[GateDecision]:
    """Load append-only gate decision history from JSONL."""
    history_path = Path(path)
    if not history_path.exists():
        return []

    decisions: list[GateDecision] = []
    with open(history_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                decisions.append(GateDecision.model_validate_json(line))
            except (ValueError, ValidationError):
                continue
    return decisions


def filter_gate_decision_history(
    decisions: list[GateDecision],
    *,
    status: str | None = None,
    last: int | None = None,
) -> list[GateDecision]:
    """Filter and truncate gate decisions for CLI display."""
    filtered = decisions
    if status:
        normalized = status.strip().lower()
        filtered = [decision for decision in filtered if decision.status == normalized]
    if last is not None and last >= 0:
        filtered = filtered[-last:]
    return filtered


def render_gate_history_markdown(decisions: list[GateDecision]) -> str:
    """Render history rows as Markdown."""
    total = len(decisions)
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for decision in decisions:
        counts[decision.status] = counts.get(decision.status, 0) + 1

    lines = ["## Gate Decision History", ""]
    lines.append(f"- Entries: {total}")
    lines.append(
        f"- Status mix: pass={counts['pass']} warn={counts['warn']} fail={counts['fail']}"
    )
    lines.append("")
    lines.append("| Created At (UTC) | Run ID | Status | Reasons |")
    lines.append("|---|---|---|---|")

    for decision in reversed(decisions):
        created_at = decision.created_at.isoformat()
        reasons = "; ".join(decision.reasons[:2]) if decision.reasons else "-"
        if len(decision.reasons) > 2:
            reasons += f" (+{len(decision.reasons) - 2} more)"
        lines.append(f"| {created_at} | {decision.run_id} | {decision.status.upper()} | {reasons} |")

    return "\n".join(lines) + "\n"
