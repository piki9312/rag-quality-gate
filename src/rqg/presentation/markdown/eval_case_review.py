"""Markdown formatter for EvalCase review."""

from __future__ import annotations

from rqg.domain import EvalCase


def _single_line(value: str) -> str:
    return value.replace("\n", " ").strip()


def _note_marker_value(notes: str | None, marker: str) -> str | None:
    if not notes:
        return None
    for part in notes.split(";"):
        stripped = part.strip()
        if stripped.startswith(marker):
            return stripped[len(marker) :]
    return None


def _manual_review_queue(cases: list[EvalCase]) -> list[tuple[EvalCase, str, str]]:
    ranked: list[tuple[int, int, str, EvalCase, str, str]] = []
    for case in cases:
        mixed = _note_marker_value(case.notes, "mixed_question:")
        split = _note_marker_value(case.notes, "split_candidate_from:")
        if mixed:
            ranked.append(
                (
                    0,
                    0 if case.risk_level == "S1" else 1,
                    case.case_id,
                    case,
                    "high",
                    f"mixed_question={mixed}",
                )
            )
        elif split:
            ranked.append(
                (
                    1,
                    0 if case.risk_level == "S1" else 1,
                    case.case_id,
                    case,
                    "medium",
                    f"split_candidate_from={split}",
                )
            )
    ranked.sort(key=lambda item: item[:3])
    return [(case, priority, reason) for _, _, _, case, priority, reason in ranked]


def render_eval_case_review_markdown(cases: list[EvalCase]) -> str:
    """Render EvalCase list into review-friendly Markdown."""
    lines: list[str] = ["# Eval Case Review", ""]

    if not cases:
        lines.extend(["No cases found.", ""])
        return "\n".join(lines)

    mixed_cases = [case for case in cases if _note_marker_value(case.notes, "mixed_question:")]
    split_cases = [
        case for case in cases if _note_marker_value(case.notes, "split_candidate_from:")
    ]
    review_queue = _manual_review_queue(cases)

    lines.extend(
        [
            "## Summary",
            "",
            f"- Total cases: {len(cases)}",
            f"- Mixed-question cases: {len(mixed_cases)}",
            f"- Split-candidate cases: {len(split_cases)}",
            f"- Manual review queue: {len(review_queue)}",
            "",
        ]
    )

    if review_queue:
        lines.extend(["## Manual Review Priority", ""])
        for case, priority, reason in review_queue:
            lines.append(
                f"1. [{priority.upper()}] {_single_line(case.case_id)} ({case.risk_level}) - "
                f"{_single_line(case.question)} [{reason}]"
            )
        lines.append("")

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

        lines.append(
            f"- Expected Answer: {_single_line(case.expected_answer) if case.expected_answer else '(none)'}"
        )

        lines.append(f"- Risk Level: {case.risk_level}")
        lines.append(f"- Document Snapshot: {_single_line(case.doc_snapshot_id)}")
        lines.append(f"- Notes: {_single_line(case.notes) if case.notes else '(none)'}")
        lines.append("")

    return "\n".join(lines)
