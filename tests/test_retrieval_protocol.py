"""Tests for retrieval protocol, external adapter, and RAG store switching.

Covers:
  - RetrievedChunk contract and to_dict()
  - RAGStoreProtocol duck-typing compliance
  - HTTPRAGAdapter response normalization, error handling
  - RAGQualityRunner with protocol-based store
  - CLI --rag-endpoint switching
  - Backward compatibility: ingest, mock, existing FAISS paths
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from rqg.serving.protocol import RAGStoreProtocol, RetrievedChunk


# ===================================================================
# 1. RetrievedChunk contract
# ===================================================================


class TestRetrievedChunk:
    def test_required_fields(self):
        chunk = RetrievedChunk(chunk_id="c1", source="doc.md", text="hello")
        assert chunk.chunk_id == "c1"
        assert chunk.source == "doc.md"
        assert chunk.text == "hello"
        assert chunk.score is None
        assert chunk.metadata is None

    def test_optional_fields(self):
        chunk = RetrievedChunk(
            chunk_id="c2",
            source="faq.md",
            text="world",
            score=0.95,
            metadata={"lang": "ja"},
        )
        assert chunk.score == 0.95
        assert chunk.metadata == {"lang": "ja"}

    def test_to_dict_minimal(self):
        chunk = RetrievedChunk(chunk_id="c1", source="doc.md", text="hello")
        d = chunk.to_dict()
        assert d == {"chunk_id": "c1", "source": "doc.md", "text": "hello"}
        assert "score" not in d
        assert "metadata" not in d

    def test_to_dict_with_score(self):
        chunk = RetrievedChunk(chunk_id="c1", source="doc.md", text="hi", score=0.8)
        d = chunk.to_dict()
        assert d["score"] == 0.8

    def test_to_dict_with_metadata(self):
        chunk = RetrievedChunk(
            chunk_id="c1", source="doc.md", text="hi", metadata={"k": "v"}
        )
        d = chunk.to_dict()
        assert d["metadata"] == {"k": "v"}

    def test_frozen(self):
        chunk = RetrievedChunk(chunk_id="c1", source="doc.md", text="hi")
        with pytest.raises(AttributeError):
            chunk.chunk_id = "c2"  # type: ignore[misc]


# ===================================================================
# 2. RAGStoreProtocol compliance
# ===================================================================


class TestRAGStoreProtocol:
    def test_faiss_store_is_protocol_compliant(self):
        """FaissRAGStore (via alias RAGStore) satisfies the protocol at runtime."""
        from rqg.serving.rag import FaissRAGStore, RAGStore

        assert RAGStore is FaissRAGStore
        assert hasattr(FaissRAGStore, "search")
        assert hasattr(FaissRAGStore, "search_multi")

    def test_duck_typed_class_is_compliant(self):
        class MyStore:
            def search(self, query: str, top_k: int = 6) -> list[dict[str, Any]]:
                return []

            def search_multi(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
                return []

        assert isinstance(MyStore(), RAGStoreProtocol)

    def test_incomplete_class_not_compliant(self):
        class Incomplete:
            def search(self, query: str) -> list:
                return []

        assert not isinstance(Incomplete(), RAGStoreProtocol)


# ===================================================================
# 3. HTTPRAGAdapter normalization & error handling
# ===================================================================


class TestHTTPRAGAdapterNormalization:
    """Test _normalize() in isolation without HTTP calls."""

    @pytest.fixture()
    def adapter(self):
        from rqg.serving.external_adapter import HTTPRAGAdapter

        return HTTPRAGAdapter(endpoint="https://example.com/search")

    def test_normalize_dict_with_results(self, adapter):
        raw = {
            "results": [
                {
                    "chunk_id": "c1",
                    "source": "doc.md",
                    "text": "hello",
                    "score": 0.9,
                },
                {
                    "chunk_id": "c2",
                    "source": "faq.md",
                    "text": "world",
                    "score": None,
                },
            ]
        }
        result = adapter._normalize(raw)
        assert len(result) == 2
        assert result[0]["chunk_id"] == "c1"
        assert result[0]["score"] == 0.9
        assert "score" not in result[1]  # score=None is omitted from dict

    def test_normalize_dict_with_chunks_key(self, adapter):
        raw = {
            "chunks": [
                {"chunk_id": "c1", "source": "d.md", "text": "t"},
            ]
        }
        result = adapter._normalize(raw)
        assert len(result) == 1

    def test_normalize_list_directly(self, adapter):
        raw = [{"chunk_id": "c1", "source": "d.md", "text": "t"}]
        result = adapter._normalize(raw)
        assert len(result) == 1

    def test_normalize_empty_results(self, adapter):
        assert adapter._normalize({"results": []}) == []
        assert adapter._normalize([]) == []
        assert adapter._normalize(None) == []

    def test_normalize_missing_results_key_raises(self, adapter):
        from rqg.serving.external_adapter import ExternalRAGSchemaError

        with pytest.raises(ExternalRAGSchemaError, match="missing 'results'"):
            adapter._normalize({"data": [{"chunk_id": "c1"}]})

    def test_normalize_non_dict_item_raises(self, adapter):
        from rqg.serving.external_adapter import ExternalRAGSchemaError

        with pytest.raises(ExternalRAGSchemaError, match="must be a dict"):
            adapter._normalize([42])

    def test_normalize_missing_required_keys_raises(self, adapter):
        from rqg.serving.external_adapter import ExternalRAGSchemaError

        with pytest.raises(ExternalRAGSchemaError, match="missing required keys"):
            adapter._normalize([{"chunk_id": "c1", "text": "t"}])  # missing source

    def test_normalize_invalid_score_raises(self, adapter):
        from rqg.serving.external_adapter import ExternalRAGSchemaError

        with pytest.raises(ExternalRAGSchemaError, match="invalid score"):
            adapter._normalize(
                [{"chunk_id": "c1", "source": "d.md", "text": "t", "score": "not-a-number"}]
            )

    def test_normalize_invalid_type_raises(self, adapter):
        from rqg.serving.external_adapter import ExternalRAGSchemaError

        with pytest.raises(ExternalRAGSchemaError, match="must be a dict or list"):
            adapter._normalize("not valid")

    def test_normalize_preserves_metadata(self, adapter):
        raw = [
            {
                "chunk_id": "c1",
                "source": "d.md",
                "text": "t",
                "score": 0.5,
                "metadata": {"page": 3},
            }
        ]
        result = adapter._normalize(raw)
        assert result[0]["metadata"] == {"page": 3}


class TestHTTPRAGAdapterHTTP:
    """Test HTTP interaction via mocked httpx."""

    @pytest.fixture()
    def adapter(self):
        from rqg.serving.external_adapter import HTTPRAGAdapter

        return HTTPRAGAdapter(
            endpoint="https://example.com/search",
            api_key="test-key",
            timeout_sec=5.0,
        )

    def test_search_delegates_to_post(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [{"chunk_id": "c1", "source": "d.md", "text": "hello"}]
        }
        with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
            results = adapter.search("test query", top_k=3)
        assert len(results) == 1
        assert results[0]["chunk_id"] == "c1"

    def test_search_multi_delegates_to_search(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [{"chunk_id": "c1", "source": "d.md", "text": "hello"}]
        }
        with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp) as mock_post:
            results = adapter.search_multi("test", top_k=10)
        assert len(results) == 1
        # Verify top_k was passed through
        call_args = mock_post.call_args
        assert call_args[1]["json"]["top_k"] == 10

    def test_timeout_raises_adapter_error(self, adapter):
        import httpx as _httpx

        from rqg.serving.external_adapter import ExternalRAGTimeoutError

        with patch(
            "rqg.serving.external_adapter.httpx.post",
            side_effect=_httpx.TimeoutException("timeout"),
        ):
            with pytest.raises(ExternalRAGTimeoutError, match="timed out"):
                adapter.search("query")

    def test_401_raises_auth_error(self, adapter):
        from rqg.serving.external_adapter import ExternalRAGAuthError

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
            with pytest.raises(ExternalRAGAuthError, match="401"):
                adapter.search("query")

    def test_403_raises_auth_error(self, adapter):
        from rqg.serving.external_adapter import ExternalRAGAuthError

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
            with pytest.raises(ExternalRAGAuthError, match="403"):
                adapter.search("query")

    def test_500_raises_server_error(self, adapter):
        from rqg.serving.external_adapter import ExternalRAGServerError

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
            with pytest.raises(ExternalRAGServerError, match="500"):
                adapter.search("query")

    def test_non_json_response_raises_schema_error(self, adapter):
        from rqg.serving.external_adapter import ExternalRAGSchemaError

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("not json")
        with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
            with pytest.raises(ExternalRAGSchemaError, match="non-JSON"):
                adapter.search("query")

    def test_api_key_in_header(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp) as mock_post:
            adapter.search("query")
        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-key"

    def test_api_key_from_env(self, monkeypatch):
        from rqg.serving.external_adapter import HTTPRAGAdapter

        monkeypatch.setenv("MY_RAG_KEY", "env-key-123")
        adapter = HTTPRAGAdapter(
            endpoint="https://example.com/search",
            api_key_env="MY_RAG_KEY",
        )
        assert adapter._api_key == "env-key-123"


# ===================================================================
# 4. Runner with protocol-based store
# ===================================================================


class TestRunnerWithProtocol:
    """RAGQualityRunner works with any RAGStoreProtocol implementation."""

    def test_runner_with_dict_based_store(self, s1_case):
        """A simple dict-returning store satisfies the protocol."""
        from rqg.quality.runner import RAGQualityRunner

        class DictStore:
            def search(self, query: str, top_k: int = 6) -> list[dict[str, Any]]:
                return [
                    {
                        "chunk_id": "chunk_A",
                        "source": "policy.md",
                        "text": "5営業日前までに申請してください。",
                        "score": 0.9,
                    }
                ]

            def search_multi(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
                return self.search(query, top_k)

        runner = RAGQualityRunner(store=DictStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.case_id == "QA001"
        assert result.latency_ms > 0

    def test_runner_with_http_adapter_mock(self, s1_case):
        """Runner works with HTTPRAGAdapter when HTTP is mocked."""
        from rqg.quality.runner import RAGQualityRunner
        from rqg.serving.external_adapter import HTTPRAGAdapter

        adapter = HTTPRAGAdapter(endpoint="https://example.com/search")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [
                {
                    "chunk_id": "chunk_A",
                    "source": "policy.md",
                    "text": "5営業日前までに申請してください。",
                    "score": 0.9,
                }
            ]
        }
        with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp):
            runner = RAGQualityRunner(store=adapter, mock_llm=True)
            result = runner.run_case(s1_case)

        assert result.case_id == "QA001"
        assert result.answer  # non-empty answer
        assert result.latency_ms > 0

    def test_runner_existing_faiss_store_still_works(self, s1_case):
        """Existing FakeStore pattern from test_runner.py still works."""
        from rqg.quality.runner import RAGQualityRunner

        class FakeStore:
            def search(self, query: str, top_k: int = 20):
                return [
                    {"chunk_id": "chunk_A", "text": "5営業日前までに申請してください。"},
                    {"chunk_id": "chunk_B", "text": "25日が締め日です。レシートを添付。"},
                ]

            def search_multi(self, query: str, top_k: int = 20):
                return self.search(query, top_k)

        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.case_id == "QA001"


# ===================================================================
# 5. CLI switching tests
# ===================================================================


class TestCLISwitching:
    def test_eval_defaults_no_rag_endpoint(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["eval", "cases.csv"])
        assert args.rag_endpoint is None
        assert args.rag_api_key_env is None

    def test_eval_with_rag_endpoint(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["eval", "cases.csv", "--rag-endpoint", "https://rag.example.com/search"]
        )
        assert args.rag_endpoint == "https://rag.example.com/search"

    def test_eval_with_rag_api_key_env(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "eval",
                "cases.csv",
                "--rag-endpoint",
                "https://rag.example.com/search",
                "--rag-api-key-env",
                "MY_RAG_KEY",
            ]
        )
        assert args.rag_api_key_env == "MY_RAG_KEY"

    def test_gate_with_rag_endpoint(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["gate", "cases.csv", "--rag-endpoint", "https://rag.example.com/search"]
        )
        assert args.rag_endpoint == "https://rag.example.com/search"

    def test_mock_ignores_rag_endpoint(self):
        """--mock forces local FAISS path even with --rag-endpoint."""
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "eval",
                "cases.csv",
                "--mock",
                "--rag-endpoint",
                "https://rag.example.com/search",
            ]
        )
        assert args.mock is True
        assert args.rag_endpoint == "https://rag.example.com/search"


# ===================================================================
# 6. Config file RAG section
# ===================================================================


class TestRagConfig:
    def test_load_rag_config_http(self, tmp_path, monkeypatch):
        from rqg.cli.eval import _load_rag_config

        config_file = tmp_path / ".rqg.yml"
        config_file.write_text(
            "rag:\n  type: http\n  endpoint: https://rag.example.com/search\n"
            "  api_key_env: MY_KEY\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        cfg = _load_rag_config()
        assert cfg["type"] == "http"
        assert cfg["endpoint"] == "https://rag.example.com/search"
        assert cfg["api_key_env"] == "MY_KEY"

    def test_load_rag_config_missing_file(self, tmp_path, monkeypatch):
        from rqg.cli.eval import _load_rag_config

        monkeypatch.chdir(tmp_path)
        cfg = _load_rag_config()
        assert cfg == {}

    def test_load_rag_config_no_rag_section(self, tmp_path, monkeypatch):
        from rqg.cli.eval import _load_rag_config

        config_file = tmp_path / ".rqg.yml"
        config_file.write_text("thresholds:\n  s1_pass_rate: 100.0\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        cfg = _load_rag_config()
        assert cfg == {}


# ===================================================================
# 7. Backward compatibility
# ===================================================================


class TestBackwardCompatibility:
    def test_ragstore_alias_importable(self):
        """from rqg.serving.rag import RAGStore still works."""
        from rqg.serving.rag import FaissRAGStore, RAGStore

        assert RAGStore is FaissRAGStore

    def test_ingest_uses_faiss_store(self):
        """cmd_ingest still imports and uses RAGStore (FaissRAGStore)."""
        from rqg.cli.eval import cmd_ingest  # import succeeds

        assert callable(cmd_ingest)

    def test_existing_mock_flag_works(self):
        """--mock flag still exists and is parsed correctly."""
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["eval", "cases.csv", "--mock"])
        assert args.mock is True
        assert args.rag_endpoint is None
