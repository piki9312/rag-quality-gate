"""Monthly summary generation for recurring quality operations."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from ..domain import GateDecision


def filter_decisions_for_month(
    decisions: list[GateDecision],
    *,
    month: str | None = None,
    now: datetime | None = None,
) -> tuple[list[GateDecision], str]:
    reference = now or datetime.now(timezone.utc)
    if month:
        month_start = datetime.fromisoformat(f"{month}-01T00:00:00+00:00")
    else:
        month_start = datetime(reference.year, reference.month, 1, tzinfo=timezone.utc)
    if month_start.month == 12:
        next_month = datetime(month_start.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(month_start.year, month_start.month + 1, 1, tzinfo=timezone.utc)
    return (
        [d for d in decisions if month_start <= d.created_at < next_month],
        month_start.date().isoformat(),
    )


def build_monthly_summary_payload(
    decisions: list[GateDecision],
    *,
    month: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    monthly_decisions, month_start = filter_decisions_for_month(decisions, month=month, now=now)
    latest = monthly_decisions[-1] if monthly_decisions else None
    blocked_runs = sum(
        1
        for decision in monthly_decisions
        if decision.status == "fail" or decision.policy_status == "block"
    )
    needs_review_runs = sum(
        1 for decision in monthly_decisions if decision.policy_status == "needs_human_review"
    )
    s1_incidents_detected = int(
        sum(
            float(decision.metrics.get("s1_fail_count", 0.0) or 0.0)
            for decision in monthly_decisions
        )
    )
    reason_counts = Counter(
        reason.strip()
        for decision in monthly_decisions
        for reason in decision.reasons
        if str(reason).strip()
    )
    resolved_issues: list[str] = []
    unresolved_issues: list[str] = []
    if monthly_decisions:
        seen_before_latest = {
            reason.strip()
            for decision in monthly_decisions[:-1]
            for reason in decision.reasons
            if str(reason).strip()
        }
        latest_reasons = (
            {reason.strip() for reason in latest.reasons if str(reason).strip()}
            if latest
            else set()
        )
        unresolved_issues = sorted(latest_reasons)
        resolved_issues = sorted(seen_before_latest - latest_reasons)

    judge_fallback_runs = sum(1 for decision in monthly_decisions if decision.judge_fallback_used)
    embedding_fallback_runs = sum(
        1 for decision in monthly_decisions if decision.embedding_fallback_used
    )
    low_reliability_runs = sum(
        1
        for decision in monthly_decisions
        if decision.judge_reliability == "low" or decision.retrieval_reliability == "low"
    )
    quality_trend_summary = _build_quality_trend_summary(monthly_decisions)
    passed_runs = sum(1 for decision in monthly_decisions if decision.status == "pass")
    s2_warnings = int(
        sum(
            1
            for decision in monthly_decisions
            for reason in decision.reasons
            if str(reason).startswith("WARN")
        )
    )

    return {
        "month": month_start[:7],
        "month_start": month_start,
        "pack_id": (
            latest.pack.pack_id or latest.pack.pack_name
            if latest is not None and latest.pack
            else None
        ),
        "total_runs": len(monthly_decisions),
        "passed_runs": passed_runs,
        "blocked_runs": blocked_runs,
        "needs_review_runs": needs_review_runs,
        "s1_incidents_detected": s1_incidents_detected,
        "s2_warnings": s2_warnings,
        "top_reasons": [
            {"reason": reason, "count": count} for reason, count in reason_counts.most_common(5)
        ],
        "top_reasons_trend": [
            {"reason": reason, "count": count} for reason, count in reason_counts.most_common(5)
        ],
        "fallback_summary": {
            "judge_fallback_count": sum(
                decision.judge_fallback_count for decision in monthly_decisions
            ),
            "embedding_fallback_count": sum(
                decision.embedding_fallback_count for decision in monthly_decisions
            ),
            "low_reliability_runs": low_reliability_runs,
        },
        "fallback_trend": {
            "judge_fallback_runs": judge_fallback_runs,
            "judge_fallback_count": sum(
                decision.judge_fallback_count for decision in monthly_decisions
            ),
            "embedding_fallback_runs": embedding_fallback_runs,
            "embedding_fallback_count": sum(
                decision.embedding_fallback_count for decision in monthly_decisions
            ),
            "low_reliability_runs": low_reliability_runs,
        },
        "resolved_issues": len(resolved_issues),
        "resolved_issue_reasons": resolved_issues,
        "unresolved_issues": len(unresolved_issues),
        "unresolved_issue_reasons": unresolved_issues,
        "recommended_actions": [
            action.model_dump(mode="json")
            for action in (latest.next_actions if latest is not None else [])
        ],
        "quality_trend_summary": quality_trend_summary,
        "quality_trend": _quality_trend_label(monthly_decisions),
        "latest_status": latest.status.upper() if latest is not None else "UNKNOWN",
        "pack": latest.pack.model_dump(mode="json") if latest is not None and latest.pack else None,
    }


def render_monthly_summary_markdown(summary: dict[str, Any]) -> str:
    lines = ["## Monthly Quality Summary", ""]
    lines.append(f"- Month start: {summary.get('month_start', '-')}")
    lines.append(f"- Total runs: {int(summary.get('total_runs', 0) or 0)}")
    lines.append(f"- Blocked runs: {int(summary.get('blocked_runs', 0) or 0)}")
    lines.append(f"- S1 incidents detected: {int(summary.get('s1_incidents_detected', 0) or 0)}")
    fallback = summary.get("fallback_trend", {}) or {}
    lines.append(
        "- Fallback trend: "
        f"judge_runs={int(fallback.get('judge_fallback_runs', 0) or 0)} "
        f"judge_count={int(fallback.get('judge_fallback_count', 0) or 0)} "
        f"embedding_runs={int(fallback.get('embedding_fallback_runs', 0) or 0)} "
        f"embedding_count={int(fallback.get('embedding_fallback_count', 0) or 0)}"
    )
    lines.append(f"- Trend summary: {summary.get('quality_trend_summary', 'n/a')}")

    top_reasons = summary.get("top_reasons_trend", []) or []
    if top_reasons:
        lines.extend(["", "### Top Reasons", "", "| Reason | Count |", "|---|---|"])
        for item in top_reasons:
            lines.append(f"| {item.get('reason', '-')} | {int(item.get('count', 0) or 0)} |")

    unresolved = summary.get("unresolved_issue_reasons", []) or []
    lines.extend(["", "### Unresolved Issues", ""])
    if unresolved:
        lines.extend(f"- {item}" for item in unresolved)
    else:
        lines.append("- None")

    resolved = summary.get("resolved_issue_reasons", []) or []
    lines.extend(["", "### Resolved Issues", ""])
    if resolved:
        lines.extend(f"- {item}" for item in resolved)
    else:
        lines.append("- None")

    actions = summary.get("recommended_actions", []) or []
    lines.extend(["", "### Recommended Actions", ""])
    if actions:
        lines.append("| Failure Category | Count | Action |")
        lines.append("|---|---|---|")
        for action in actions:
            failure_category = action.get("failure_category", "-")
            count = int(action.get("count", 0) or 0)
            action_text = str(action.get("action", "-")).replace("|", "\\|")
            lines.append(f"| {failure_category} | {count} | {action_text} |")
    else:
        lines.append("- No recommended actions in the latest run.")

    return "\n".join(lines) + "\n"


def _build_quality_trend_summary(decisions: list[GateDecision]) -> str:
    if not decisions:
        return "No monthly runs found."
    first = decisions[0]
    latest = decisions[-1]
    overall_start = float(first.metrics.get("overall_pass_rate", 0.0) or 0.0)
    overall_end = float(latest.metrics.get("overall_pass_rate", 0.0) or 0.0)
    s1_start = float(first.metrics.get("s1_pass_rate", 0.0) or 0.0)
    s1_end = float(latest.metrics.get("s1_pass_rate", 0.0) or 0.0)
    return (
        f"Overall pass rate {overall_start:.1f}% -> {overall_end:.1f}%; "
        f"S1 pass rate {s1_start:.1f}% -> {s1_end:.1f}%; "
        f"latest status={latest.status.upper()}"
    )


def _quality_trend_label(decisions: list[GateDecision]) -> str:
    if len(decisions) < 2:
        return "stable"
    first = decisions[0]
    latest = decisions[-1]
    overall_start = float(first.metrics.get("overall_pass_rate", 0.0) or 0.0)
    overall_end = float(latest.metrics.get("overall_pass_rate", 0.0) or 0.0)
    if overall_end > overall_start:
        return "improving"
    if overall_end < overall_start:
        return "declining"
    return "stable"
