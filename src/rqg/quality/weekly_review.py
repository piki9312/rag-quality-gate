"""Helpers for exporting weekly review issue payloads."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping


DEFAULT_WEEKLY_REVIEW_TITLE_PREFIX = "[Phase2.5][Weekly Review]"
DEFAULT_WEEKLY_REVIEW_LABELS = ["phase2-5", "weekly-review", "ops"]


def build_weekly_review_issue_payload(
    summary_payload: Mapping[str, Any],
    *,
    week_start: str | None = None,
    title_prefix: str = DEFAULT_WEEKLY_REVIEW_TITLE_PREFIX,
    title_suffix: str = "",
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Build a GitHub issue create/update payload from a history summary payload."""
    labels = labels or list(DEFAULT_WEEKLY_REVIEW_LABELS)
    comparison = _mapping(summary_payload.get("comparison"))
    trend = _mapping(summary_payload.get("trend"))
    coverage = _mapping(summary_payload.get("failure_action_coverage"))
    status_mix = _mapping(summary_payload.get("status_mix"))
    uncovered_categories = _list_of_mappings(summary_payload.get("uncovered_categories"))
    stale_case_review = _mapping(summary_payload.get("stale_case_review"))
    stale_owner_rollup = _list_of_mappings(stale_case_review.get("owners"))
    stale_cases = _list_of_mappings(stale_case_review.get("stale_cases"))
    review_steward = str(summary_payload.get("review_steward", "")).strip()
    week_start = (
        str(week_start or "").strip()
        or str(summary_payload.get("week_start", "")).strip()
        or _current_week_start_iso()
    )

    latest_run_id = str(
        trend.get("latest_run_id")
        or comparison.get("current_run_id")
        or "unknown-run"
    )
    latest_status = str(
        trend.get("latest_status")
        or comparison.get("current_status")
        or "UNKNOWN"
    )
    uncovered_count = len(uncovered_categories)
    stale_case_count = len(stale_cases)
    issue_needed = uncovered_count > 0 or stale_case_count > 0

    title = f"{title_prefix.strip() or DEFAULT_WEEKLY_REVIEW_TITLE_PREFIX} {week_start}"
    if title_suffix.strip():
        title = f"{title} {title_suffix.strip()}"

    body_lines = [
        f"Week start: {week_start}",
        "",
        "## Triage Summary",
        "",
        f"- Weekly review steward: {review_steward or 'unassigned'}",
        f"- Latest run: {latest_run_id}",
        f"- Latest status: {latest_status}",
        f"- History entries: {int(summary_payload.get('entries', 0) or 0)}",
        (
            "- Status mix: "
            f"pass={int(status_mix.get('pass', 0) or 0)} "
            f"warn={int(status_mix.get('warn', 0) or 0)} "
            f"fail={int(status_mix.get('fail', 0) or 0)}"
        ),
    ]

    if coverage:
        body_lines.append(
            "- Failure action coverage: "
            f"{int(coverage.get('covered_categories', 0) or 0)}/"
            f"{int(coverage.get('total_categories', 0) or 0)} categories "
            f"({float(coverage.get('coverage_rate', 0.0) or 0.0):.1f}%)"
        )

    if stale_case_review:
        body_lines.append(
            "- Fresh case review rate: "
            f"{float(stale_case_review.get('fresh_case_review_rate', 0.0) or 0.0):.1f}% "
            f"({int(stale_case_review.get('fresh_case_count', 0) or 0)}/"
            f"{int(stale_case_review.get('total_cases', 0) or 0)}) within "
            f"{int(stale_case_review.get('stale_after_days', 0) or 0)} days"
        )

    body_lines.append(
        "- Action required: "
        + _format_action_required_line(
            uncovered_count=uncovered_count,
            stale_case_count=stale_case_count,
        )
    )

    body_lines.extend(
        [
            "",
            "## Current Signals",
        ]
    )

    body_lines.extend(["", "### Uncovered Categories", ""])
    if uncovered_categories:
        body_lines.append("| Failure Category | Count | Last Seen Run | Affected Cases |")
        body_lines.append("|---|---|---|---|")
        for item in uncovered_categories:
            affected_case_ids = [str(case_id) for case_id in item.get("affected_case_ids", [])]
            affected_cases = ", ".join(affected_case_ids) if affected_case_ids else "-"
            body_lines.append(
                f"| {item.get('failure_category', '-')} | {int(item.get('total_count', 0) or 0)} | "
                f"{item.get('last_seen_run_id', '-')} | {affected_cases} |"
            )
    else:
        body_lines.append("- No uncovered failure categories in the current history window.")

    body_lines.extend(["", "### Stale Cases By Owner", ""])
    if stale_owner_rollup:
        body_lines.append("| Owner | Stale Cases | Highest Age Days | Case IDs |")
        body_lines.append("|---|---|---|---|")
        for item in stale_owner_rollup:
            case_ids = ", ".join(str(case_id) for case_id in item.get("case_ids", [])) or "-"
            highest_age_days = item.get("highest_age_days")
            age_text = str(highest_age_days) if highest_age_days is not None else "-"
            body_lines.append(
                f"| {item.get('owner', 'unassigned')} | {int(item.get('stale_count', 0) or 0)} | {age_text} | {case_ids} |"
            )
    else:
        body_lines.append("- No stale active cases in the latest gate summary.")

    if stale_cases:
        body_lines.extend(["", "### Latest Stale Cases", ""])
        body_lines.append("| Case | Owner | Severity | Age Days | Reference | Issue |")
        body_lines.append("|---|---|---|---|---|---|")
        for item in stale_cases:
            reference = str(item.get("reference_field", "-") or "-")
            reference_value = str(item.get("reference_value", "")).strip()
            if reference_value:
                reference = f"{reference}={reference_value}".strip("=")
            age_days = item.get("age_days")
            age_text = str(age_days) if age_days is not None else "-"
            issue_text = str(item.get("issue", "-") or "-")
            body_lines.append(
                f"| {item.get('case_id', '-')} | {item.get('owner', 'unassigned')} | {item.get('severity', '-')} | {age_text} | {reference or '-'} | {issue_text} |"
            )

    body_lines.extend(["", "## Required Actions", ""])
    if issue_needed:
        body_lines.extend(
            [
                "- [ ] Review uncovered failure categories and confirm first_action coverage in quality-pack.yml.",
                "- [ ] Assign owner and due date for stale or uncovered items.",
                "- [ ] Record warn-only, no-data, or override exceptions when they affected this week.",
                "- [ ] Close this issue after stale and uncovered items are cleared or explicitly accepted.",
            ]
        )
    else:
        body_lines.extend(
            [
                "- [ ] Review the recent history summary below and close or archive this issue if no follow-up is needed.",
                "- [ ] Record any steward-owned operational follow-up discovered during the weekly review.",
            ]
        )

    summary_lines = [str(line) for line in summary_payload.get("summary_lines", [])]
    if summary_lines:
        body_lines.extend(["", "## Recent History", ""])
        body_lines.extend(_normalize_summary_lines(summary_lines))

    body_lines.extend(
        [
            "",
            "## References",
            "- docs/ops/operations/phase2-5-weekly-metrics-register.md",
            "- docs/ops/operations/phase2-5-investigate-response-flow.md",
            "- docs/ops/operations/phase2-5-ws2-failure-review-template.md",
            "- docs/ops/operations/phase2-5-ws3-gate-exception-approval-template.md",
            "- docs/ops/operations/phase2-5-case-quality-weekly-review.md",
        ]
    )

    return {
        "title": title.strip(),
        "body": "\n".join(body_lines).strip() + "\n",
        "labels": labels,
        "issue_needed": issue_needed,
        "review_steward": review_steward or None,
        "summary": {
            "week_start": week_start,
            "latest_run_id": latest_run_id,
            "latest_status": latest_status,
            "entries": int(summary_payload.get("entries", 0) or 0),
            "coverage_rate": float(coverage.get("coverage_rate", 0.0) or 0.0) if coverage else 0.0,
            "uncovered_categories_count": uncovered_count,
            "stale_cases_count": stale_case_count,
        },
        "uncovered_categories": uncovered_categories,
        "stale_case_review": stale_case_review,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            items.append(dict(item))
    return items


def _current_week_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=now.weekday())).date().isoformat()


def _format_action_required_line(*, uncovered_count: int, stale_case_count: int) -> str:
    if uncovered_count <= 0 and stale_case_count <= 0:
        return "no immediate owner action (0 uncovered categories, 0 stale active cases)"

    parts: list[str] = []
    if uncovered_count > 0:
        parts.append(f"{uncovered_count} uncovered categor{'y' if uncovered_count == 1 else 'ies'}")
    if stale_case_count > 0:
        parts.append(f"{stale_case_count} stale active case{'s' if stale_case_count != 1 else ''}")
    return ", ".join(parts)


def _normalize_summary_lines(lines: list[str]) -> list[str]:
    normalized: list[str] = []
    for line in lines:
        if not line.startswith("#"):
            normalized.append(line)
            continue

        heading_markers = len(line) - len(line.lstrip("#"))
        heading_text = line[heading_markers:].lstrip()
        normalized_level = min(6, heading_markers + 1)
        normalized.append("#" * normalized_level + " " + heading_text)
    return normalized