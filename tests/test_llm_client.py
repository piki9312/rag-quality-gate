"""Tests for llm_client — cost estimation, client init, answer generation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rqg.serving.llm_client import estimate_cost, generate_answer, get_openai_client

# ------------------------------------------------------------------
# estimate_cost
# ------------------------------------------------------------------


class TestEstimateCost:
    def test_known_model(self):
        cost = estimate_cost("gpt-4o-mini", input_tokens=1000, output_tokens=500)
        assert cost is not None
        assert cost > 0
        # gpt-4o-mini: 0.00015/1K in + 0.0006/1K out
        expected = 0.00015 + 0.0003
        assert cost == pytest.approx(expected, abs=1e-6)

    def test_unknown_model_returns_none(self):
        cost = estimate_cost("unknown-model", input_tokens=1000, output_tokens=500)
        assert cost is None

    def test_zero_tokens(self):
        cost = estimate_cost("gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_gpt4_turbo_pricing(self):
        cost = estimate_cost("gpt-4-turbo", input_tokens=2000, output_tokens=1000)
        assert cost is not None
        # gpt-4-turbo: 0.01/1K in + 0.03/1K out
        expected = 0.02 + 0.03
        assert cost == pytest.approx(expected, abs=1e-6)


# ------------------------------------------------------------------
# get_openai_client
# ------------------------------------------------------------------


class TestGetOpenaiClient:
    def test_raises_without_api_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("# no key here\n", encoding="utf-8")
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            get_openai_client(env_path=str(env_file))

    def test_reads_key_from_env_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=sk-test-key-12345\n", encoding="utf-8")
        client = get_openai_client(env_path=str(env_file))
        assert client is not None

    def test_reads_key_from_environ(self, monkeypatch, tmp_path):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
        # point to nonexistent .env so it falls through to environ
        client = get_openai_client(env_path=str(tmp_path / "missing.env"))
        assert client is not None


# ------------------------------------------------------------------
# generate_answer (mocked)
# ------------------------------------------------------------------


class TestGenerateAnswer:
    def test_generates_answer_from_chunks(self, monkeypatch):
        mock_result = {
            "text": "回答テスト [policy.md@abc#chunk0]",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "estimated_cost_usd": 0.001,
            },
        }
        monkeypatch.setattr(
            "rqg.serving.llm_client.call_openai_chat",
            lambda *a, **kw: mock_result,
        )
        chunks = [
            {"chunk_id": "policy.md@abc#chunk0", "source": "policy.md", "text": "有給は5営業日前"},
        ]
        answer, meta = generate_answer("有給の期限は？", chunks)
        assert "回答テスト" in answer
        assert meta["usage"]["total_tokens"] == 150
        assert meta["context_chars"] > 0

    def test_empty_chunks_produces_context(self, monkeypatch):
        mock_result = {
            "text": "回答なし",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "estimated_cost_usd": 0.0,
            },
        }
        monkeypatch.setattr(
            "rqg.serving.llm_client.call_openai_chat",
            lambda *a, **kw: mock_result,
        )
        answer, meta = generate_answer("test", [])
        assert meta["context_chars"] == 0
