"""Shared reason and reliability codes for Proof Gate artifacts."""

from __future__ import annotations

from typing import Final

REASON_RETRIEVAL_FAIL: Final = "retrieval_fail"
REASON_ANSWER_QUALITY_FAIL: Final = "answer_quality_fail"
REASON_EVIDENCE_MISMATCH: Final = "evidence_mismatch"
REASON_BAD_JSON: Final = "bad_json"
REASON_SCHEMA_FAIL: Final = "schema_fail"
REASON_LATENCY_FAIL: Final = "latency_fail"
REASON_SAFETY_FAIL: Final = "safety_fail"
REASON_TIMEOUT: Final = "timeout"
REASON_PROVIDER_ERROR: Final = "provider_error"
REASON_JUDGE_FALLBACK_USED: Final = "judge_fallback_used"
REASON_JUDGE_UNRELIABLE: Final = "judge_unreliable"
REASON_EMBEDDING_FALLBACK_USED: Final = "embedding_fallback_used"
REASON_NEEDS_HUMAN_REVIEW: Final = "needs_human_review"

FAILURE_NONE: Final = "none"
FAILURE_PARSE_ERROR: Final = "parse_error"
FAILURE_SCHEMA_ERROR: Final = "schema_error"
FAILURE_TIMEOUT: Final = "timeout"
FAILURE_PROVIDER_ERROR: Final = "provider_error"
FAILURE_EMPTY_JUDGE_RESPONSE: Final = "empty_judge_response"
FAILURE_INVALID_SCORE: Final = "invalid_score"
FAILURE_FALLBACK_MOCK_JUDGE: Final = "fallback_mock_judge"
FAILURE_EMBEDDING_FALLBACK: Final = "embedding_fallback"
FAILURE_RETRIEVAL_EMPTY: Final = "retrieval_empty"
FAILURE_UNKNOWN: Final = "unknown"

REASON_ALIASES: Final[dict[str, str]] = {
    "retrieval_miss": REASON_RETRIEVAL_FAIL,
    "bad_reference": REASON_EVIDENCE_MISMATCH,
    "keyword_miss": REASON_ANSWER_QUALITY_FAIL,
    "synthesis": REASON_ANSWER_QUALITY_FAIL,
    "schema_error": REASON_SCHEMA_FAIL,
    "tool_failure": REASON_PROVIDER_ERROR,
    "judge_reliability": REASON_JUDGE_UNRELIABLE,
    "embedding_reliability": REASON_EMBEDDING_FALLBACK_USED,
    "human_review": REASON_NEEDS_HUMAN_REVIEW,
}


def canonical_reason(value: object) -> str:
    """Return a stable reason code while preserving unknown existing strings."""
    normalized = str(value or "").strip()
    if not normalized:
        return FAILURE_UNKNOWN
    return REASON_ALIASES.get(normalized, normalized)


def classify_judge_failure_type(reason: str | None) -> str | None:
    """Map judge fallback text to the public failure taxonomy."""
    normalized = str(reason or "").strip().lower()
    if not normalized:
        return None
    if "parse" in normalized or "json" in normalized:
        return FAILURE_PARSE_ERROR
    if "schema" in normalized or "config" in normalized:
        return FAILURE_SCHEMA_ERROR
    if "timeout" in normalized:
        return FAILURE_TIMEOUT
    if "empty" in normalized:
        return FAILURE_EMPTY_JUDGE_RESPONSE
    if "score" in normalized:
        return FAILURE_INVALID_SCORE
    if "mock" in normalized:
        return FAILURE_FALLBACK_MOCK_JUDGE
    if "api" in normalized or "provider" in normalized or "connection" in normalized:
        return FAILURE_PROVIDER_ERROR
    return FAILURE_UNKNOWN
