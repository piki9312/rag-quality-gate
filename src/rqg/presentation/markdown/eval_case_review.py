"""Markdown formatter for EvalCase review."""

from __future__ import annotations

from rqg.domain import EvalCase


def _single_line(value: str) -> str:
    return value.replace("\n", " ").strip()


def render_eval_case_review_markdown(cases: list[EvalCase]) -> str:
    """Render EvalCase list into review-friendly Markdown."""
    lines: list[str] = ["# Eval Case Review", ""]

    if not cases:
        lines.extend(["No cases found.", ""])
        return "\n".join(lines)

    for case in cases:
        lines.append(f"## Case: {_single_line(case.case_id)}")
        lines.append(f"- Question: {_single_line(case.question)}")
        lines.append("- Expected Evidence:")
        if case.expected_evidence:
            lines.extend(
                f"  - {_single_line(evidence_id)}" for evidence_id in case.expected_evidence
            )
        else:
            lines.append("  - (none)")

        lines.append("- Expected Keywords:")
        if case.expected_keywords:
            lines.extend(f"  - {_single_line(keyword)}" for keyword in case.expected_keywords)
        else:
            lines.append("  - (none)")

        lines.append(f"- Risk Level: {case.risk_level}")
        lines.append(f"- Document Snapshot: {_single_line(case.doc_snapshot_id)}")
        lines.append(f"- Notes: {_single_line(case.notes) if case.notes else '(none)'}")
        lines.append("")

    return "\n".join(lines)
