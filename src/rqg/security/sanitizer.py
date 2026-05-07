"""Shared sanitization helpers for operator-facing output."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

REDACTED = "[REDACTED]"

_URL_RE = re.compile(r"(?i)\b(?:https?|wss?)://[^\s<>()\[\]{}]+")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SK_API_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{6,}\b")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|authorization)\b\s*[:=]\s*[^\s,;]+"
)
_CONTENT_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(prompt|answer|expected_answer|ai_answer|retrieved_evidence|chunk_text)\b\s*[:=]\s*[^;,\n]+"
)
_CONTENT_INLINE_RE = re.compile(
    r"(?i)\b(retrieved evidence|retrieved_evidence|chunk text|chunk_text|prompt text)\b"
)
_SECRET_WORD_RE = re.compile(
    r"\b(?:[A-Z0-9_]*(?:TOKEN|SECRET|API_KEY|APIKEY|PASSWORD)[A-Z0-9_-]*)\b"
)
_WINDOWS_PATH_RE = re.compile(r"(?i)\b[A-Z]:\\(?:[^\\\s]+\\)*[^\\\s]+")
_UNIX_PATH_RE = re.compile(r"(?<![\w.-])/(?:[^/\s]+/)*[^/\s]+")
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_text(value: str | None) -> str:
    text = str(value or "")
    if not text:
        return ""

    sanitized = text
    sanitized = _URL_RE.sub(REDACTED, sanitized)
    sanitized = _BEARER_RE.sub(f"Bearer {REDACTED}", sanitized)
    sanitized = _SK_API_KEY_RE.sub(REDACTED, sanitized)
    sanitized = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}={REDACTED}", sanitized)
    sanitized = _CONTENT_ASSIGNMENT_RE.sub(REDACTED, sanitized)
    sanitized = _CONTENT_INLINE_RE.sub(REDACTED, sanitized)
    sanitized = _SECRET_WORD_RE.sub(REDACTED, sanitized)
    sanitized = _WINDOWS_PATH_RE.sub(REDACTED, sanitized)
    sanitized = _UNIX_PATH_RE.sub(REDACTED, sanitized)
    return sanitized


def sanitize_error_message(value: str | None) -> str:
    sanitized = sanitize_text(value)
    return _WHITESPACE_RE.sub(" ", sanitized).strip()


def sanitize_endpoint(value: str | None) -> str:
    return REDACTED if str(value or "").strip() else ""


def sanitize_query_text(value: str | None) -> str:
    return REDACTED if str(value or "").strip() else ""


def sanitize_source_ref(value: str | None) -> str:
    return REDACTED if str(value or "").strip() else ""


def sanitize_artifact_path(value: str | Path | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None
    if _URL_RE.search(text):
        return REDACTED

    path = Path(text)
    if path.is_absolute() or _WINDOWS_PATH_RE.fullmatch(text):
        return path.name or REDACTED
    return text.replace("\\", "/")


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_payload(item) for key, item in value.items()}
    return value
