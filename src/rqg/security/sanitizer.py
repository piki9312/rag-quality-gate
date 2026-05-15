"""Shared sanitizers for logs, reports, notifications, and issue payloads."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, quote_plus, urlsplit, urlunsplit

REDACTED = "[REDACTED]"

_SENSITIVE_KEYS = {
    "prompt",
    "question",
    "answer",
    "ai_answer",
    "expected_answer",
    "retrieved_evidence",
    "evidence",
    "chunk_text",
    "text",
    "source_path",
    "endpoint",
    "url",
    "token",
    "api_key",
    "authorization",
    "password",
    "secret",
}

_SAFE_KEYS = {
    "status",
    "policy_status",
    "pass_rate",
    "s1_failed_count",
    "failure_category",
    "reason_code",
    "reason_codes",
    "run_id",
    "case_id",
    "count",
    "score",
    "latency_ms",
    "created_at",
}

_SECRET_QUERY_KEYS = {
    "token",
    "api_key",
    "apikey",
    "access_token",
    "signature",
    "sig",
    "secret",
    "password",
}

_TOKEN_PATTERNS = [
    re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{16,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}"),
    re.compile(r"(?i)\b(api_key|access_token|token|signature|secret)=([^&\s]{16,})"),
    re.compile(r"\b[A-Za-z0-9_]{32,}\b"),
]

_URL_PATTERN = re.compile(r"https?://[^\s)>\]\"']+")
_WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r"\b[A-Za-z]:\\[^\s]+")
_POSIX_INTERNAL_PATH_PATTERN = re.compile(r"(?<!\w)/(home|Users|var|tmp|workspace)/[^\s]+")


def redact_text(value: object) -> str:
    """Redact token-like strings, sensitive URLs, and internal source paths."""
    text = "" if value is None else str(value)
    if not text:
        return text

    redacted = text
    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    redacted = _URL_PATTERN.sub(lambda match: sanitize_url(match.group(0)), redacted)
    redacted = _WINDOWS_ABSOLUTE_PATH_PATTERN.sub(REDACTED, redacted)
    redacted = _POSIX_INTERNAL_PATH_PATTERN.sub(REDACTED, redacted)
    return redacted


def sanitize_error_message(value: object) -> str:
    """Sanitize free-form exception or external error text."""
    return redact_text(value)


def sanitize_url(value: object) -> str:
    """Redact endpoint URLs and URLs carrying secret-bearing query parameters."""
    raw_url = "" if value is None else str(value).strip()
    if not raw_url:
        return raw_url

    try:
        parts = urlsplit(raw_url)
    except ValueError:
        return REDACTED if contains_token_like_string(raw_url) else redact_text(raw_url)

    if parts.scheme in {"http", "https"}:
        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        has_secret_query = any(key.lower() in _SECRET_QUERY_KEYS for key, _ in query_pairs)
        if has_secret_query:
            safe_query = "&".join(
                f"{quote_plus(key)}="
                f"{REDACTED if key.lower() in _SECRET_QUERY_KEYS else quote_plus(value)}"
                for key, value in query_pairs
            )
            safe_url = urlunsplit((parts.scheme, parts.netloc, parts.path, safe_query, ""))
            return safe_url
        return REDACTED

    return REDACTED if contains_token_like_string(raw_url) else raw_url


def sanitize_source_ref(value: object) -> str:
    """Sanitize a source reference while preserving short document IDs."""
    source_ref = "" if value is None else str(value).strip()
    if not source_ref:
        return source_ref
    if _URL_PATTERN.search(source_ref):
        return sanitize_url(source_ref)
    if _WINDOWS_ABSOLUTE_PATH_PATTERN.search(source_ref) or _POSIX_INTERNAL_PATH_PATTERN.search(
        source_ref
    ):
        return REDACTED
    return redact_text(source_ref)


def sanitize_mapping(payload: dict) -> dict:
    """Return a sanitized copy of a mapping."""
    return _sanitize_value(payload)


def contains_token_like_string(value: object) -> bool:
    """Return True if value appears to contain a token or credential."""
    text = "" if value is None else str(value)
    return any(pattern.search(text) for pattern in _TOKEN_PATTERNS)


def _sanitize_value(value: Any, *, key: str | None = None) -> Any:
    normalized_key = (key or "").strip().lower()
    if normalized_key in _SENSITIVE_KEYS:
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(item_key): _sanitize_value(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, str):
        if normalized_key in _SAFE_KEYS:
            return redact_text(value)
        if normalized_key in {"source", "source_ref", "reference", "reference_value"}:
            return sanitize_source_ref(value)
        return redact_text(value)
    return value
