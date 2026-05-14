"""Gate decision history helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import ValidationError

from ..domain import GateDecision
from .staleness import CaseStalenessItem

_TRACKED_HISTORY_METRICS: tuple[tuple[str, str, str], ...] = (
    ("overall_pass_rate", "Overall pass rate", "pct"),
    ("s1_pass_rate", "S1 pass rate", "pct"),
    ("fresh_case_review_rate", "Fresh case review rate", "pct"),
    ("avg_faithfulness", "Avg faithfulness", "pct"),
    ("avg_judge_relevance", "Avg judge relevance", "pct"),
    ("avg_evidence_recall", "Avg expected evidence recall", "pct"),
    ("stale_case_count", "Stale case count", "count"),
    ("current_runs", "Current runs", "count"),
    ("baseline_runs", "Baseline runs", "count"),
)

_DEFAULT_NEXT_ACTION_HINT = "Define next action in weekly review issue"


@dataclass(frozen=True, slots=True)
class GateMetricDelta:
    key: str
    label: str
    current: float | None
    previous: float | None
    delta: float | None
    unit: str


@dataclass(frozen=True, slots=True)
class GateActionDelta:
    failure_category: str
    current_count: int
    previous_count: int
    delta: int


@dataclass(frozen=True, slots=True)
class GateDecisionComparison:
    current_run_id: str
    previous_run_id: str
    current_status: str
    previous_status: str
    metric_deltas: list[GateMetricDelta]
    new_reasons: list[str]
    resolved_reasons: list[str]
    action_deltas: list[GateActionDelta]


@dataclass(frozen=True, slots=True)
class GateHistoryTrend:
    latest_run_id: str
    latest_status: str
    streak_count: int
    status_sequence: list[str]
    metric_deltas: list[GateMetricDelta]
    window_size: int


@dataclass(frozen=True, slots=True)
class GateActionCoverageItem:
    failure_category: str
    total_count: int
    last_seen_run_id: str
    covered: bool
    affected_case_ids: list[str]


@dataclass(frozen=True, slots=True)
class GateFailureActionCoverage:
    total_categories: int
    covered_categories: int
    coverage_rate: float
    uncovered_categories: list[GateActionCoverageItem]
    window_size: int


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


def compare_gate_decisions(
    current: GateDecision,
    previous: GateDecision,
) -> GateDecisionComparison:
    """Compare two gate decisions and summarize operationally relevant changes."""
    metric_deltas = _build_metric_deltas(current, previous)
    current_reasons = _normalize_strings(current.reasons)
    previous_reasons = _normalize_strings(previous.reasons)
    previous_reason_set = set(previous_reasons)
    current_reason_set = set(current_reasons)

    new_reasons = [reason for reason in current_reasons if reason not in previous_reason_set]
    resolved_reasons = [reason for reason in previous_reasons if reason not in current_reason_set]

    current_actions = _action_counts(current)
    previous_actions = _action_counts(previous)
    action_deltas: list[GateActionDelta] = []
    for category in sorted(set(current_actions) | set(previous_actions)):
        current_count = current_actions.get(category, 0)
        previous_count = previous_actions.get(category, 0)
        if current_count == previous_count:
            continue
        action_deltas.append(
            GateActionDelta(
                failure_category=category,
                current_count=current_count,
                previous_count=previous_count,
                delta=current_count - previous_count,
            )
        )

    return GateDecisionComparison(
        current_run_id=current.run_id,
        previous_run_id=previous.run_id,
        current_status=current.status.upper(),
        previous_status=previous.status.upper(),
        metric_deltas=metric_deltas,
        new_reasons=new_reasons,
        resolved_reasons=resolved_reasons,
        action_deltas=action_deltas,
    )


def build_gate_history_comparison(
    decisions: list[GateDecision],
    *,
    compare_offset: int = 1,
) -> GateDecisionComparison | None:
    """Compare the latest gate decision with an earlier entry in history."""
    if compare_offset < 1 or len(decisions) <= compare_offset:
        return None

    current = decisions[-1]
    previous = decisions[-(compare_offset + 1)]
    return compare_gate_decisions(current, previous)


def summarize_gate_history(
    decisions: list[GateDecision],
    *,
    trend_window: int = 5,
) -> GateHistoryTrend | None:
    """Summarize recent status and metric movement across history."""
    if not decisions or trend_window < 1:
        return None

    window = decisions[-trend_window:]
    latest = decisions[-1]
    latest_status = latest.status.upper()
    streak_count = 0
    for decision in reversed(decisions):
        if decision.status.upper() != latest_status:
            break
        streak_count += 1

    metric_deltas = _build_metric_deltas(window[-1], window[0])

    return GateHistoryTrend(
        latest_run_id=latest.run_id,
        latest_status=latest_status,
        streak_count=streak_count,
        status_sequence=[decision.status.upper() for decision in window],
        metric_deltas=metric_deltas,
        window_size=len(window),
    )


def summarize_failure_action_coverage(
    decisions: list[GateDecision],
    *,
    trend_window: int = 5,
) -> GateFailureActionCoverage | None:
    """Summarize recent coverage of concrete next actions by failure category."""
    if not decisions or trend_window < 1:
        return None

    window = decisions[-trend_window:]
    categories: dict[str, GateActionCoverageItem] = {}
    for decision in window:
        for action in decision.next_actions:
            existing = categories.get(action.failure_category)
            total_count = action.count if existing is None else existing.total_count + action.count
            categories[action.failure_category] = GateActionCoverageItem(
                failure_category=action.failure_category,
                total_count=total_count,
                last_seen_run_id=decision.run_id,
                covered=_is_structured_action(action.action),
                affected_case_ids=list(action.affected_case_ids),
            )

    if not categories:
        return None

    items = sorted(
        categories.values(),
        key=lambda item: (-item.total_count, item.failure_category),
    )
    uncovered = [item for item in items if not item.covered]
    covered_categories = len(items) - len(uncovered)
    coverage_rate = (covered_categories / len(items)) * 100.0
    return GateFailureActionCoverage(
        total_categories=len(items),
        covered_categories=covered_categories,
        coverage_rate=coverage_rate,
        uncovered_categories=uncovered,
        window_size=len(window),
    )


def build_gate_history_summary_payload(
    decisions: list[GateDecision],
    *,
    compare_offset: int = 1,
    trend_window: int = 5,
    stale_cases: list[CaseStalenessItem] | None = None,
    stale_after_days: int = 0,
    fresh_case_review_rate: float | None = None,
    fresh_case_count: int = 0,
    fresh_case_total: int = 0,
    review_steward: str | None = None,
) -> dict[str, object]:
    """Build machine-readable recent-history summary payload for reports and CI."""
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for decision in decisions:
        counts[decision.status] = counts.get(decision.status, 0) + 1

    trend = summarize_gate_history(decisions, trend_window=trend_window)
    coverage = summarize_failure_action_coverage(decisions, trend_window=trend_window)
    comparison = build_gate_history_comparison(decisions, compare_offset=compare_offset)
    summary_lines = build_gate_history_summary_lines(
        decisions,
        compare_offset=compare_offset,
        trend_window=trend_window,
    )

    uncovered_categories = (
        []
        if coverage is None
        else [_serialize_action_coverage_item(item) for item in coverage.uncovered_categories]
    )
    stale_case_review = _build_stale_case_review_payload(
        stale_cases or [],
        stale_after_days=stale_after_days,
        fresh_case_review_rate=fresh_case_review_rate,
        fresh_case_count=fresh_case_count,
        fresh_case_total=fresh_case_total,
    )

    return {
        "entries": len(decisions),
        "status_mix": counts,
        "execution_mode": decisions[-1].execution_mode if decisions else None,
        "week_start": _week_start_iso(decisions[-1].created_at) if decisions else None,
        "compare_offset": compare_offset,
        "trend_window": trend_window,
        "summary_lines": summary_lines,
        "trend": _serialize_history_trend(trend),
        "comparison": _serialize_history_comparison(comparison),
        "failure_action_coverage": _serialize_failure_action_coverage(coverage),
        "uncovered_categories": uncovered_categories,
        "stale_case_review": stale_case_review,
        "reliability": _serialize_reliability(decisions[-1]) if decisions else None,
        "review_steward": (review_steward or "").strip() or None,
    }


def build_gate_history_summary_lines(
    decisions: list[GateDecision],
    *,
    compare_offset: int = 1,
    trend_window: int = 5,
) -> list[str]:
    """Build reusable recent-history summary lines for CLI and gate reports."""
    trend = summarize_gate_history(decisions, trend_window=trend_window)
    coverage = summarize_failure_action_coverage(decisions, trend_window=trend_window)
    comparison = build_gate_history_comparison(decisions, compare_offset=compare_offset)

    lines: list[str] = []
    latest = decisions[-1] if decisions else None
    if trend is not None:
        lines.append(f"- Latest status: {trend.latest_status} ({trend.latest_run_id})")
        if latest is not None and getattr(latest, "execution_mode", None):
            lines.append(f"- Execution mode: {latest.execution_mode}")
        lines.append(f"- Current streak: {trend.latest_status} x{trend.streak_count}")
        if len(trend.status_sequence) > 1:
            sequence = " -> ".join(trend.status_sequence)
            lines.append(
                f"- Recent sequence (oldest -> latest, last {trend.window_size}): {sequence}"
            )
        for metric in _select_visible_metric_deltas(
            trend.metric_deltas,
            include_unchanged_labels={"Overall pass rate", "S1 pass rate"},
        ):
            lines.append(f"- {metric.label} trend: {_format_metric_transition(metric)}")

    if coverage is not None:
        lines.append(
            "- Failure action coverage "
            f"(last {coverage.window_size}): {coverage.covered_categories}/"
            f"{coverage.total_categories} categories ({coverage.coverage_rate:.1f}%)"
        )
        if coverage.uncovered_categories:
            lines.append(
                f"- Uncovered categories: {_summarize_action_coverage_items(coverage.uncovered_categories, limit=5)}"
            )

    if latest is not None:
        lines.append(f"- Judge reliability: {latest.judge_reliability.upper()}")
        if latest.judge_fallback_count > 0:
            lines.append(f"- Judge fallback count: {latest.judge_fallback_count}")
        if latest.judge_failure_types:
            failure_types = ", ".join(
                f"{failure_type}={count}"
                for failure_type, count in sorted(latest.judge_failure_types.items())
            )
            lines.append(f"- Judge failure types: {failure_types}")
        if latest.embedding_fallback_used:
            lines.append(
                "- Embedding fallback: "
                f"YES ({latest.embedding_fallback_reason or 'fallback detected'})"
            )
        if latest.needs_human_review:
            lines.append("- Needs human review: YES")
        else:
            lines.append("- Needs human review: NO")

    if comparison is not None:
        lines.append("")
        lines.append("### Latest Change Summary")
        lines.append(
            f"- Compared runs: {comparison.previous_run_id} -> {comparison.current_run_id}"
        )
        if comparison.previous_status == comparison.current_status:
            lines.append(f"- Status change: unchanged ({comparison.current_status})")
        else:
            lines.append(
                f"- Status change: {comparison.previous_status} -> {comparison.current_status}"
            )

        visible_metric_deltas = _select_visible_metric_deltas(comparison.metric_deltas)
        if visible_metric_deltas:
            for metric in visible_metric_deltas:
                lines.append(f"- {metric.label}: {_format_metric_transition(metric)}")
        else:
            lines.append("- Metric deltas: no tracked metric changes")

        if comparison.new_reasons:
            lines.append(f"- New reasons: {_summarize_items(comparison.new_reasons, limit=3)}")
        if comparison.resolved_reasons:
            lines.append(
                f"- Resolved reasons: {_summarize_items(comparison.resolved_reasons, limit=3)}"
            )
        if comparison.action_deltas:
            lines.append("- Failure action deltas:")
            for action_delta in comparison.action_deltas:
                lines.append(
                    "  - "
                    f"{action_delta.failure_category}: {action_delta.previous_count} -> "
                    f"{action_delta.current_count} ({_format_count_delta(action_delta.delta)})"
                )
        current_decision = decisions[-1]
        previous_decision = decisions[-(compare_offset + 1)]
        if previous_decision.judge_reliability != current_decision.judge_reliability:
            lines.append(
                "- Judge reliability change: "
                f"{previous_decision.judge_reliability.upper()} -> "
                f"{current_decision.judge_reliability.upper()}"
            )
        if previous_decision.needs_human_review != current_decision.needs_human_review:
            lines.append(
                "- Needs human review change: "
                f"{'YES' if previous_decision.needs_human_review else 'NO'} -> "
                f"{'YES' if current_decision.needs_human_review else 'NO'}"
            )

    return lines


def render_gate_history_markdown(
    decisions: list[GateDecision],
    *,
    compare_offset: int = 1,
    trend_window: int = 5,
) -> str:
    """Render history rows as Markdown."""
    total = len(decisions)
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for decision in decisions:
        counts[decision.status] = counts.get(decision.status, 0) + 1

    lines = ["## Gate Decision History", ""]
    lines.append(f"- Entries: {total}")
    lines.append(f"- Status mix: pass={counts['pass']} warn={counts['warn']} fail={counts['fail']}")
    lines.extend(
        build_gate_history_summary_lines(
            decisions,
            compare_offset=compare_offset,
            trend_window=trend_window,
        )
    )

    lines.append("")
    lines.append("| Created At (UTC) | Run ID | Status | Reasons |")
    lines.append("|---|---|---|---|")

    for decision in reversed(decisions):
        created_at = decision.created_at.isoformat()
        reasons = "; ".join(decision.reasons[:2]) if decision.reasons else "-"
        if len(decision.reasons) > 2:
            reasons += f" (+{len(decision.reasons) - 2} more)"
        lines.append(
            f"| {created_at} | {decision.run_id} | {decision.status.upper()} | {reasons} |"
        )

    return "\n".join(lines) + "\n"


def _build_metric_deltas(current: GateDecision, previous: GateDecision) -> list[GateMetricDelta]:
    deltas: list[GateMetricDelta] = []
    for key, label, unit in _TRACKED_HISTORY_METRICS:
        current_value = _coerce_metric(current.metrics.get(key))
        previous_value = _coerce_metric(previous.metrics.get(key))
        if current_value is None and previous_value is None:
            continue
        delta = None
        if current_value is not None and previous_value is not None:
            delta = current_value - previous_value
        deltas.append(
            GateMetricDelta(
                key=key,
                label=label,
                current=current_value,
                previous=previous_value,
                delta=delta,
                unit=unit,
            )
        )
    return deltas


def _coerce_metric(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_strings(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            normalized.append(text)
    return normalized


def _action_counts(decision: GateDecision) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in decision.next_actions:
        counts[action.failure_category] = counts.get(action.failure_category, 0) + action.count
    return counts


def _select_visible_metric_deltas(
    metric_deltas: list[GateMetricDelta],
    *,
    include_unchanged_labels: set[str] | None = None,
) -> list[GateMetricDelta]:
    include_unchanged_labels = include_unchanged_labels or set()
    visible: list[GateMetricDelta] = []
    for metric in metric_deltas:
        changed = metric.delta is None or abs(metric.delta) > 1e-9
        if changed or metric.label in include_unchanged_labels:
            visible.append(metric)
    return visible


def _format_metric_transition(metric: GateMetricDelta) -> str:
    previous = _format_metric_value(metric.previous, metric.unit)
    current = _format_metric_value(metric.current, metric.unit)
    if metric.delta is None:
        return f"{previous} -> {current}"
    return f"{previous} -> {current} ({_format_metric_delta(metric.delta, metric.unit)})"


def _format_metric_value(value: float | None, unit: str) -> str:
    if value is None:
        return "n/a"
    if unit == "count":
        return f"{value:.0f}"
    return f"{value:.1f}%"


def _format_metric_delta(delta: float, unit: str) -> str:
    sign = "+" if delta > 0 else ""
    if unit == "count":
        return f"{sign}{delta:.0f}"
    return f"{sign}{delta:.1f} pts"


def _format_count_delta(delta: int) -> str:
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta}"


def _serialize_metric_delta(metric: GateMetricDelta) -> dict[str, object]:
    return {
        "key": metric.key,
        "label": metric.label,
        "current": metric.current,
        "previous": metric.previous,
        "delta": metric.delta,
        "unit": metric.unit,
    }


def _serialize_reliability(decision: GateDecision) -> dict[str, object]:
    return {
        "judge_fallback_used": decision.judge_fallback_used,
        "judge_fallback_count": decision.judge_fallback_count,
        "judge_failure_types": decision.judge_failure_types,
        "judge_reliability": decision.judge_reliability,
        "embedding_fallback_used": decision.embedding_fallback_used,
        "embedding_fallback_count": decision.embedding_fallback_count,
        "embedding_fallback_reason": decision.embedding_fallback_reason,
        "retrieval_reliability": decision.retrieval_reliability,
        "fallback_summary": decision.fallback_summary,
        "policy_status": decision.policy_status,
        "needs_human_review": decision.needs_human_review,
    }


def _serialize_action_delta(action_delta: GateActionDelta) -> dict[str, object]:
    return {
        "failure_category": action_delta.failure_category,
        "current_count": action_delta.current_count,
        "previous_count": action_delta.previous_count,
        "delta": action_delta.delta,
    }


def _serialize_history_comparison(
    comparison: GateDecisionComparison | None,
) -> dict[str, object] | None:
    if comparison is None:
        return None
    return {
        "current_run_id": comparison.current_run_id,
        "previous_run_id": comparison.previous_run_id,
        "current_status": comparison.current_status,
        "previous_status": comparison.previous_status,
        "metric_deltas": [_serialize_metric_delta(metric) for metric in comparison.metric_deltas],
        "new_reasons": comparison.new_reasons,
        "resolved_reasons": comparison.resolved_reasons,
        "action_deltas": [
            _serialize_action_delta(action_delta) for action_delta in comparison.action_deltas
        ],
    }


def _serialize_history_trend(trend: GateHistoryTrend | None) -> dict[str, object] | None:
    if trend is None:
        return None
    created_at = None
    if isinstance(trend.latest_run_id, str):
        created_at = None
    return {
        "latest_run_id": trend.latest_run_id,
        "latest_status": trend.latest_status,
        "streak_count": trend.streak_count,
        "status_sequence": trend.status_sequence,
        "metric_deltas": [_serialize_metric_delta(metric) for metric in trend.metric_deltas],
        "window_size": trend.window_size,
    }


def _serialize_action_coverage_item(item: GateActionCoverageItem) -> dict[str, object]:
    return {
        "failure_category": item.failure_category,
        "total_count": item.total_count,
        "last_seen_run_id": item.last_seen_run_id,
        "covered": item.covered,
        "affected_case_ids": item.affected_case_ids,
    }


def _serialize_failure_action_coverage(
    coverage: GateFailureActionCoverage | None,
) -> dict[str, object] | None:
    if coverage is None:
        return None
    return {
        "total_categories": coverage.total_categories,
        "covered_categories": coverage.covered_categories,
        "coverage_rate": coverage.coverage_rate,
        "uncovered_categories": [
            _serialize_action_coverage_item(item) for item in coverage.uncovered_categories
        ],
        "window_size": coverage.window_size,
    }


def _build_stale_case_review_payload(
    stale_cases: list[CaseStalenessItem],
    *,
    stale_after_days: int,
    fresh_case_review_rate: float | None,
    fresh_case_count: int,
    fresh_case_total: int,
) -> dict[str, object] | None:
    if (
        stale_after_days <= 0
        and fresh_case_review_rate is None
        and fresh_case_total <= 0
        and not stale_cases
    ):
        return None

    owner_rollup: dict[str, dict[str, object]] = {}
    for item in stale_cases:
        owner = item.owner.strip() or "unassigned"
        bucket = owner_rollup.setdefault(
            owner,
            {
                "owner": owner,
                "stale_count": 0,
                "case_ids": [],
                "highest_age_days": None,
            },
        )
        bucket["stale_count"] = int(bucket["stale_count"]) + 1
        bucket["case_ids"].append(item.case_id)
        if item.age_days is not None:
            highest_age_days = bucket.get("highest_age_days")
            if highest_age_days is None or item.age_days > highest_age_days:
                bucket["highest_age_days"] = item.age_days

    owners = sorted(
        owner_rollup.values(),
        key=lambda item: (-int(item["stale_count"]), str(item["owner"])),
    )
    serialized_stale_cases = [_serialize_stale_case_item(item) for item in stale_cases]
    return {
        "stale_after_days": stale_after_days,
        "fresh_case_review_rate": fresh_case_review_rate,
        "fresh_case_count": fresh_case_count,
        "total_cases": fresh_case_total,
        "stale_cases_count": len(stale_cases),
        "owners": owners,
        "stale_cases": serialized_stale_cases,
    }


def _serialize_stale_case_item(item: CaseStalenessItem) -> dict[str, object]:
    return {
        "case_id": item.case_id,
        "name": item.name,
        "severity": item.severity,
        "owner": item.owner.strip() or "unassigned",
        "reference_field": item.reference_field,
        "reference_value": item.reference_value,
        "age_days": item.age_days,
        "issue": item.issue,
    }


def _is_structured_action(action: str) -> bool:
    normalized = str(action).strip()
    return bool(normalized) and normalized.lower() != _DEFAULT_NEXT_ACTION_HINT.lower()


def _summarize_action_coverage_items(
    items: list[GateActionCoverageItem],
    *,
    limit: int,
) -> str:
    trimmed = items[:limit]
    summary = "; ".join(
        f"{item.failure_category} ({item.total_count} case{'s' if item.total_count != 1 else ''})"
        for item in trimmed
    )
    remaining = len(items) - len(trimmed)
    if remaining > 0:
        summary += f" (+{remaining} more)"
    return summary or "-"


def _summarize_items(items: list[str], *, limit: int) -> str:
    trimmed = items[:limit]
    summary = "; ".join(trimmed)
    remaining = len(items) - len(trimmed)
    if remaining > 0:
        summary += f" (+{remaining} more)"
    return summary or "-"


def _week_start_iso(value: datetime) -> str:
    timestamp = value.astimezone(timezone.utc)
    return (timestamp - timedelta(days=timestamp.weekday())).date().isoformat()
