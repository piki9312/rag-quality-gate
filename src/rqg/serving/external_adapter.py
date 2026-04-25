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


_REQUIRED_RESULT_FIELDS = ("chunk_id", "source", "text")


def _available_fields(value: Any) -> str:
    if not isinstance(value, dict):
        return "(none)"
    keys = sorted(str(key) for key in value.keys())
    return ", ".join(keys) if keys else "(none)"


def _response_mapping_hint() -> str:
    return (
        "Fix hint: adjust response_mapping or the external adapter response so "
        "retrieval results map to results[].chunk_id, results[].source, and results[].text."
    )


def _schema_context(value: Any) -> str:
    return f"Available fields: {_available_fields(value)}. {_response_mapping_hint()}"


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
    ):
        if httpx is None:
            raise ImportError(
                "httpx is required for HTTPRAGAdapter. "
                "Install it with: pip install rag-quality-gate[external]"
            )
        self.endpoint = endpoint.rstrip("/")
        self.timeout_sec = timeout_sec

        resolved_key = api_key
        if resolved_key is None and api_key_env:
            resolved_key = os.environ.get(api_key_env)
        self._api_key = resolved_key

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 6) -> list[dict[str, Any]]:
        """外部 RAG API を呼び出し、結果を正規化して返す。"""
        payload: dict[str, Any] = {"query": query, "top_k": top_k}
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

        # results キーがある場合はその中身を使う
        if isinstance(raw, dict):
            results = raw.get("results", raw.get("chunks", None))
            if results is None:
                raise ExternalRAGSchemaError(
                    "External RAG response missing 'results' or 'chunks' key. "
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

        normalized: list[dict[str, Any]] = []
        for i, item in enumerate(results):
            if not isinstance(item, dict):
                raise ExternalRAGSchemaError(
                    f"External RAG result item [{i}] must be a dict, " f"got {type(item).__name__}"
                )
            # Validate required fields
            missing = [k for k in _REQUIRED_RESULT_FIELDS if k not in item]
            if missing:
                raise ExternalRAGSchemaError(
                    f"External RAG result item [{i}] missing required keys: {missing}. "
                    f"{_schema_context(item)}"
                )
            values = {key: str(item[key]).strip() for key in _REQUIRED_RESULT_FIELDS}
            empty = [key for key, value in values.items() if not value]
            if empty:
                raise ExternalRAGSchemaError(
                    f"External RAG result item [{i}] has empty required fields: {empty}. "
                    "Empty answer/context symptoms usually mean the external response fields "
                    "are mapped incorrectly or the upstream retrieval returned empty content. "
                    f"{_schema_context(item)}"
                )

            score: float | None = None
            raw_score = item.get("score")
            if raw_score is not None:
                try:
                    score = float(raw_score)
                except (TypeError, ValueError) as exc:
                    raise ExternalRAGSchemaError(
                        f"External RAG result item [{i}] has invalid score "
                        f"value {raw_score!r}: {exc}"
                    ) from exc

            chunk = RetrievedChunk(
                chunk_id=values["chunk_id"],
                source=values["source"],
                text=values["text"],
                score=score,
                metadata=item.get("metadata"),
            )
            normalized.append(chunk.to_dict())

        return normalized
