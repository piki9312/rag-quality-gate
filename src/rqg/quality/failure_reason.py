"""Failure reason classification helpers for actionable quality triage."""

from __future__ import annotations

from typing import Literal

FailureCategory = Literal[
    "retrieval_miss",
    "stale",
    "synthesis",
    "tool_failure",
    "unknown",
]


def classify_failure_category(
    *,
    failure_type: str | None,
    failure_reason: str,
    retrieval_hit: bool | None,
    retrieved_ids: list[str],
) -> FailureCategory:
    """Classify raw failure signals into a stable actionable category."""
    failure_type_normalized = (failure_type or "").strip().lower()
    reason_normalized = failure_reason.strip().lower()

    if failure_type_normalized == "error":
        return "tool_failure"
    if failure_type_normalized == "retrieval_miss":
        return "retrieval_miss"
    if failure_type_normalized == "bad_reference":
        return "synthesis"
    if failure_type_normalized == "keyword_miss":
        if retrieval_hit is False or not retrieved_ids:
            return "retrieval_miss"
        if any(token in reason_normalized for token in ["stale", "outdated", "obsolete"]):
            return "stale"
        return "synthesis"

    if any(token in reason_normalized for token in ["timeout", "connection", "api", "rate limit"]):
        return "tool_failure"
    if any(token in reason_normalized for token in ["not found", "no data", "empty retrieval"]):
        return "retrieval_miss"

    return "unknown"
