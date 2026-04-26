"""HTTP ベースの外部 RAG adapter。

外部 RAG API を ``RAGStoreProtocol`` 契約に適合させる。
レスポンスを ``RetrievedChunk`` 相当の dict に正規化し、
runner にHTTP詳細や生レスポンスを漏らさない。

外部 API のレスポンス想定 (``results`` 配列):
    [
        {
            "chunk_id": "doc-abc#3",
            "source": "policy.md",
            "text": "...",
            "score": 0.87,
            "metadata": { ... }          # optional
        },
        ...
    ]
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

from .protocol import RetrievedChunk

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions — adapter 層で文脈付きエラーに変換する
# ---------------------------------------------------------------------------


class ExternalRAGError(Exception):
    """外部RAG adapter で発生したエラーの基底。"""


class ExternalRAGTimeoutError(ExternalRAGError):
    """外部 RAG API がタイムアウトした。"""


class ExternalRAGAuthError(ExternalRAGError):
    """外部 RAG API が 401/403 を返した。"""


class ExternalRAGServerError(ExternalRAGError):
    """外部 RAG API が 5xx を返した。"""


class ExternalRAGSchemaError(ExternalRAGError):
    """外部 RAG API のレスポンスが期待するスキーマに合致しない。"""


@dataclass(frozen=True, slots=True)
class ExternalRAGResponseMapping:
    answer_path: str = "answer"
    results_path: str = "results"
    chunk_id_path: str = "chunk_id"
    source_path: str = "source"
    text_path: str = "text"
    score_path: str | None = "score"


@dataclass(frozen=True, slots=True)
class ExternalRAGRequestMapping:
    question_field: str = "query"
    top_k_field: str | None = "top_k"


@dataclass(frozen=True, slots=True)
class ExternalRAGAdapterConfig:
    endpoint: str
    method: str = "POST"
    timeout_sec: float = 30.0
    api_key_env: str | None = None
    request_mapping: ExternalRAGRequestMapping = field(default_factory=ExternalRAGRequestMapping)
    response_mapping: ExternalRAGResponseMapping = field(default_factory=ExternalRAGResponseMapping)


def _available_fields(value: Any) -> str:
    if not isinstance(value, dict):
        return "(none)"
    keys = sorted(str(key) for key in value.keys())
    return ", ".join(keys) if keys else "(none)"


def _get_path(value: Any, path: str | None) -> tuple[bool, Any]:
    if not path:
        return False, None
    current = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _response_mapping_hint() -> str:
    return (
        "Fix hint: adjust response_mapping or the external adapter response so "
        "retrieval results map to results[].chunk_id, results[].source, and results[].text."
    )


def _schema_context(value: Any) -> str:
    return f"Available fields: {_available_fields(value)}. {_response_mapping_hint()}"


def load_http_rag_adapter_config(path: str | Path) -> ExternalRAGAdapterConfig:
    """Load an adapter_config.yml file without exposing secrets."""
    import yaml

    config_path = Path(path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ExternalRAGSchemaError(
            f"adapter_config must be a YAML object: {config_path.as_posix()}"
        )

    adapter = data.get("adapter", {})
    if not isinstance(adapter, dict):
        raise ExternalRAGSchemaError("adapter_config.adapter must be an object")
    if str(adapter.get("type", "http")).lower() != "http":
        raise ExternalRAGSchemaError("adapter_config.adapter.type must be 'http'")

    endpoint = str(adapter.get("endpoint") or "").strip()
    if not endpoint:
        raise ExternalRAGSchemaError("adapter_config.adapter.endpoint is required")

    auth = adapter.get("auth", {})
    if auth is None:
        auth = {}
    if not isinstance(auth, dict):
        raise ExternalRAGSchemaError("adapter_config.adapter.auth must be an object")

    api_key_env = auth.get("token_env") or auth.get("api_key_env")
    method = str(adapter.get("method", "POST")).upper()
    timeout_sec = float(adapter.get("timeout_seconds", adapter.get("timeout_sec", 30.0)))

    request_mapping_payload = data.get("request_mapping", adapter.get("request_mapping", {}))
    if request_mapping_payload is None:
        request_mapping_payload = {}
    if not isinstance(request_mapping_payload, dict):
        raise ExternalRAGSchemaError("adapter_config.request_mapping must be an object")

    response_mapping_payload = data.get("response_mapping", adapter.get("response_mapping", {}))
    if response_mapping_payload is None:
        response_mapping_payload = {}
    if not isinstance(response_mapping_payload, dict):
        raise ExternalRAGSchemaError("adapter_config.response_mapping must be an object")

    legacy_fields = response_mapping_payload.get("fields")
    if isinstance(legacy_fields, dict):
        response_mapping_payload = {
            **response_mapping_payload,
            "chunk_id_path": response_mapping_payload.get("chunk_id_path")
            or legacy_fields.get("chunk_id"),
            "source_path": response_mapping_payload.get("source_path")
            or legacy_fields.get("source"),
            "text_path": response_mapping_payload.get("text_path") or legacy_fields.get("text"),
            "score_path": response_mapping_payload.get("score_path") or legacy_fields.get("score"),
        }

    return ExternalRAGAdapterConfig(
        endpoint=endpoint,
        method=method,
        timeout_sec=timeout_sec,
        api_key_env=str(api_key_env).strip() if api_key_env else None,
        request_mapping=ExternalRAGRequestMapping(
            question_field=str(request_mapping_payload.get("question_field", "query")),
            top_k_field=(
                str(request_mapping_payload["top_k_field"])
                if request_mapping_payload.get("top_k_field")
                else "top_k"
            ),
        ),
        response_mapping=ExternalRAGResponseMapping(
            answer_path=str(response_mapping_payload.get("answer_path", "answer")),
            results_path=str(response_mapping_payload.get("results_path", "results")),
            chunk_id_path=str(response_mapping_payload.get("chunk_id_path", "chunk_id")),
            source_path=str(response_mapping_payload.get("source_path", "source")),
            text_path=str(response_mapping_payload.get("text_path", "text")),
            score_path=(
                str(response_mapping_payload["score_path"])
                if response_mapping_payload.get("score_path")
                else None
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class HTTPRAGAdapter:
    """HTTP ベースの外部 RAG を ``RAGStoreProtocol`` に適合させる adapter。

    Parameters
    ----------
    endpoint:
        外部 RAG 検索 API の URL (例: ``https://rag.example.com/api/search``)。
    api_key:
        API キー。``None`` の場合は ``api_key_env`` から取得。
    api_key_env:
        API キーを格納する環境変数名。``api_key`` が ``None`` の場合に参照。
    timeout_sec:
        HTTP リクエストのタイムアウト秒数。
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str | None = None,
        api_key_env: str | None = None,
        timeout_sec: float = 30.0,
        method: str = "POST",
        request_mapping: ExternalRAGRequestMapping | None = None,
        response_mapping: ExternalRAGResponseMapping | None = None,
    ):
        if httpx is None:
            raise ImportError(
                "httpx is required for HTTPRAGAdapter. "
                "Install it with: pip install rag-quality-gate[external]"
            )
        self.endpoint = endpoint.rstrip("/")
        self.timeout_sec = timeout_sec
        self.method = method.upper()
        if self.method != "POST":
            raise ExternalRAGSchemaError(
                f"External RAG adapter only supports POST today, got method={self.method!r}"
            )
        self.request_mapping = request_mapping or ExternalRAGRequestMapping()
        self._explicit_response_mapping = response_mapping is not None
        self.response_mapping = response_mapping or ExternalRAGResponseMapping(
            answer_path="",
            results_path="results",
            chunk_id_path="chunk_id",
            source_path="source",
            text_path="text",
            score_path="score",
        )

        resolved_key = api_key
        if resolved_key is None and api_key_env:
            resolved_key = os.environ.get(api_key_env)
        self._api_key = resolved_key

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 6) -> list[dict[str, Any]]:
        """外部 RAG API を呼び出し、結果を正規化して返す。"""
        payload: dict[str, Any] = {self.request_mapping.question_field: query}
        if self.request_mapping.top_k_field:
            payload[self.request_mapping.top_k_field] = top_k
        raw = self._post(payload)
        return self._normalize(raw)

    def search_multi(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        """search(top_k=...) に委譲する。

        外部RAG側が multi-query をサポートしている場合は将来的にオーバーライド可能。
        """
        return self.search(query, top_k=top_k)

    def get_reliability_snapshot(self) -> dict[str, object]:
        return {
            "embedding_fallback_used": False,
            "embedding_fallback_reason": None,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _post(self, payload: dict[str, Any]) -> Any:
        """HTTP POST を実行し、JSON レスポンスを返す。

        HTTP エラーを adapter 層の例外に変換する。
        """
        try:
            resp = httpx.post(
                self.endpoint,
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout_sec,
            )
        except httpx.TimeoutException as exc:
            raise ExternalRAGTimeoutError(
                f"External RAG API timed out after {self.timeout_sec}s: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalRAGError(f"External RAG API request failed: {exc}") from exc

        if resp.status_code in (401, 403):
            raise ExternalRAGAuthError(
                f"External RAG API returned {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code >= 500:
            raise ExternalRAGServerError(
                f"External RAG API returned {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code != 200:
            raise ExternalRAGError(
                f"External RAG API returned unexpected status {resp.status_code}: "
                f"{resp.text[:200]}"
            )

        try:
            return resp.json()
        except Exception as exc:
            raise ExternalRAGSchemaError(
                f"External RAG API returned non-JSON response: {exc}"
            ) from exc

    def _normalize(self, raw: Any) -> list[dict[str, Any]]:
        """外部レスポンスを ``RetrievedChunk`` 互換 dict のリストに変換する。

        * 空結果 → 空配列 (通常動作)
        * スキーマ不整合 → ``ExternalRAGSchemaError``
        """
        if raw is None:
            return []

        mapping = self.response_mapping

        # results キーがある場合はその中身を使う
        if isinstance(raw, dict):
            if mapping.answer_path:
                answer_exists, answer = _get_path(raw, mapping.answer_path)
                if not answer_exists:
                    raise ExternalRAGSchemaError(
                        f"External RAG response missing answer_path '{mapping.answer_path}'. "
                        f"{_schema_context(raw)}"
                    )
                if str(answer or "").strip() == "":
                    raise ExternalRAGSchemaError(
                        f"External RAG response has empty answer at answer_path "
                        f"'{mapping.answer_path}'. {_schema_context(raw)}"
                    )

            results_exists, results = _get_path(raw, mapping.results_path)
            if (
                not results_exists
                and not self._explicit_response_mapping
                and mapping.results_path == "results"
            ):
                results_exists, results = _get_path(raw, "chunks")
            if not results_exists:
                if not self._explicit_response_mapping and mapping.results_path == "results":
                    raise ExternalRAGSchemaError(
                        "External RAG response missing 'results' or 'chunks' key. "
                        f"{_schema_context(raw)}"
                    )
                raise ExternalRAGSchemaError(
                    f"External RAG response missing results_path '{mapping.results_path}'. "
                    f"{_schema_context(raw)}"
                )
        elif isinstance(raw, list):
            results = raw
        else:
            raise ExternalRAGSchemaError(
                f"External RAG response must be a dict or list, got {type(raw).__name__}"
            )

        if not results:
            return []
        if not isinstance(results, list):
            raise ExternalRAGSchemaError(
                f"External RAG results_path '{mapping.results_path}' must resolve to a list, "
                f"got {type(results).__name__}. {_schema_context(raw)}"
            )

        normalized: list[dict[str, Any]] = []
        for i, item in enumerate(results):
            if not isinstance(item, dict):
                raise ExternalRAGSchemaError(
                    f"External RAG result item [{i}] must be a dict, " f"got {type(item).__name__}"
                )
            text_exists, raw_text = _get_path(item, mapping.text_path)
            if not text_exists:
                raise ExternalRAGSchemaError(
                    f"External RAG result item [{i}] missing text_path '{mapping.text_path}'. "
                    f"{_schema_context(item)}"
                )
            text = str(raw_text or "").strip()
            if not text:
                raise ExternalRAGSchemaError(
                    f"External RAG result item [{i}] has empty text_path '{mapping.text_path}'. "
                    "Empty answer/context symptoms usually mean the external response fields "
                    "are mapped incorrectly or the upstream retrieval returned empty content. "
                    f"{_schema_context(item)}"
                )

            diagnostics: list[str] = []
            chunk_id_exists, raw_chunk_id = _get_path(item, mapping.chunk_id_path)
            if chunk_id_exists and str(raw_chunk_id or "").strip():
                chunk_id = str(raw_chunk_id).strip()
            else:
                chunk_id = f"external-result-{i + 1}"
                diagnostics.append(
                    f"missing optional chunk_id_path '{mapping.chunk_id_path}'; generated {chunk_id}"
                )

            source_exists, raw_source = _get_path(item, mapping.source_path)
            if source_exists and str(raw_source or "").strip():
                source = str(raw_source).strip()
            else:
                source = "external-rag"
                diagnostics.append(
                    f"missing optional source_path '{mapping.source_path}'; using external-rag"
                )

            score: float | None = None
            score_exists, raw_score = _get_path(item, mapping.score_path)
            if score_exists and raw_score is not None:
                try:
                    score = float(raw_score)
                except (TypeError, ValueError) as exc:
                    raise ExternalRAGSchemaError(
                        f"External RAG result item [{i}] has invalid score "
                        f"value {raw_score!r}: {exc}"
                    ) from exc
            elif mapping.score_path:
                diagnostics.append(f"missing optional score_path '{mapping.score_path}'")

            chunk = RetrievedChunk(
                chunk_id=chunk_id,
                source=source,
                text=text,
                score=score,
                metadata=_metadata_with_diagnostics(item.get("metadata"), diagnostics),
            )
            normalized.append(chunk.to_dict())

        return normalized


def _metadata_with_diagnostics(raw_metadata: Any, diagnostics: list[str]) -> dict[str, Any] | None:
    metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
    if diagnostics:
        metadata = {**metadata, "mapping_warnings": diagnostics}
    return metadata or None
