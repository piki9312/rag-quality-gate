"""External RAG connection validation helpers."""

from __future__ import annotations

import time

from ..domain import ConnectionValidationResult
from .external_adapter import (
    ExternalRAGAuthError,
    ExternalRAGError,
    ExternalRAGSchemaError,
    ExternalRAGServerError,
    ExternalRAGTimeoutError,
    HTTPRAGAdapter,
)


def validate_http_rag_connection(
    *,
    endpoint: str,
    query: str,
    top_k: int = 3,
    api_key_env: str | None = None,
    timeout_sec: float = 10.0,
) -> ConnectionValidationResult:
    """Validate an external HTTP RAG endpoint against the retrieved-chunk contract."""
    started = time.perf_counter()
    adapter = HTTPRAGAdapter(
        endpoint=endpoint,
        api_key_env=api_key_env,
        timeout_sec=timeout_sec,
    )

    try:
        results = adapter.search(query, top_k=top_k)
    except ExternalRAGTimeoutError as exc:
        return _error_result(
            endpoint=endpoint,
            query=query,
            top_k=top_k,
            started=started,
            error_type="timeout_error",
            issue=str(exc),
        )
    except ExternalRAGAuthError as exc:
        return _error_result(
            endpoint=endpoint,
            query=query,
            top_k=top_k,
            started=started,
            error_type="auth_error",
            issue=str(exc),
        )
    except ExternalRAGServerError as exc:
        return _error_result(
            endpoint=endpoint,
            query=query,
            top_k=top_k,
            started=started,
            error_type="server_error",
            issue=str(exc),
        )
    except ExternalRAGSchemaError as exc:
        return _error_result(
            endpoint=endpoint,
            query=query,
            top_k=top_k,
            started=started,
            error_type="schema_error",
            issue=str(exc),
        )
    except ExternalRAGError as exc:
        return _error_result(
            endpoint=endpoint,
            query=query,
            top_k=top_k,
            started=started,
            error_type="request_error",
            issue=str(exc),
        )

    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    sample_chunk_ids = [
        str(item.get("chunk_id", "")) for item in results[:5] if item.get("chunk_id")
    ]
    sample_sources = [str(item.get("source", "")) for item in results[:5] if item.get("source")]

    return ConnectionValidationResult(
        endpoint=endpoint,
        query=query,
        top_k=top_k,
        ok=True,
        latency_ms=latency_ms,
        chunk_count=len(results),
        sample_chunk_ids=sample_chunk_ids,
        sample_sources=sample_sources,
        checked_at=_utcnow(),
    )


def _error_result(
    *,
    endpoint: str,
    query: str,
    top_k: int,
    started: float,
    error_type: ConnectionValidationResult.__annotations__["error_type"],
    issue: str,
) -> ConnectionValidationResult:
    return ConnectionValidationResult(
        endpoint=endpoint,
        query=query,
        top_k=top_k,
        ok=False,
        error_type=error_type,
        latency_ms=round((time.perf_counter() - started) * 1000, 1),
        issues=[issue],
        checked_at=_utcnow(),
    )


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
