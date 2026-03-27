"""Markdown formatter for ImpactReport review."""

from __future__ import annotations

from collections import OrderedDict

from rqg.domain import ImpactDetail, ImpactReport


def _single_line(value: str) -> str:
    return value.replace("\n", " ").strip()


def render_impact_report_review_markdown(report: ImpactReport) -> str:
    """Render an ImpactReport into review-friendly Markdown."""
    lines: list[str] = [
        "# Impact Report Review",
        "",
        f"- Old Snapshot: {_single_line(report.old_snapshot_id)}",
        f"- New Snapshot: {_single_line(report.new_snapshot_id)}",
        "",
        "## Changed Evidence",
    ]

    if report.changed_evidence_ids:
        lines.extend(f"- {_single_line(evidence_id)}" for evidence_id in report.changed_evidence_ids)
    else:
        lines.append("- (none)")

    lines.extend(["", "## Impacted Cases", ""])

    # Group details by case while preserving appearance order.
    grouped: OrderedDict[str, list[ImpactDetail]] = OrderedDict()
    for detail in report.details:
        case_id = detail.case_id.strip() or "(unknown-case)"
        grouped.setdefault(case_id, []).append(detail)

    if grouped:
        for case_id, details in grouped.items():
            lines.append(f"### Case: {_single_line(case_id)}")
            question = details[0].question.strip()
            lines.append(f"- Question: {_single_line(question) if question else '(none)'}")
            for detail in details:
                matched_evidence_id = detail.matched_evidence_id.strip()
                lines.append(
                    f"- Matched Evidence: {_single_line(matched_evidence_id) if matched_evidence_id else '(none)'}"
                )
            lines.append("")
    else:
        if report.impacted_case_ids:
            for case_id in report.impacted_case_ids:
                lines.append(f"### Case: {_single_line(case_id)}")
                lines.append("- Question: (none)")
                lines.append("- Matched Evidence: (none)")
                lines.append("")
        else:
            lines.append("- (none)")
            lines.append("")

    return "\n".join(lines)
