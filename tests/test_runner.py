"""Tests for RAGQualityRunner — mock LLM & mock store でE2E評価。"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rqg.quality.models import EvalResult, EvalRun, QATestCase
from rqg.quality.runner import RAGQualityRunner

# ------------------------------------------------------------------
# Mock RAGStore
# ------------------------------------------------------------------


class FakeStore:
    """RAGStore のモック — search() はダミーチャンクを返す。"""

    def search(self, query: str, top_k: int = 20):
        return [
            {"chunk_id": "chunk_A", "text": "5営業日前までに申請してください。"},
            {"chunk_id": "chunk_B", "text": "25日が締め日です。レシートを添付。"},
            {"chunk_id": "chunk_C", "text": "在宅勤務は週2回まで可能。"},
        ]

    def search_multi(self, query: str, top_k: int = 20):
        return self.search(query, top_k)


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


class TestRunCase:
    def test_s1_pass_mock_llm(self, s1_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        # Mock LLM は chunk テキストを結合 → "5営業日前" が含まれる
        assert result.case_id == "QA001"
        assert result.latency_ms > 0

    def test_s2_pass_mock_llm(self, s2_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s2_case)
        assert result.case_id == "QA002"
        # "25日" と "レシート" が結合テキストに含まれるはず
        assert "25日" in result.answer

    def test_retrieval_hit_detected(self, s1_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.retrieval_hit is True  # chunk_A が返ってくる

    def test_retrieval_miss(self, s1_case):
        s1_case.expected_chunks = ["chunk_X"]
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.retrieval_hit is False
        # S1 + retrieval miss → passed=False
        assert result.passed is False
        assert result.failure_category == "retrieval_miss"

    def test_error_handling(self, s1_case):
        """store.search がエラーを投げたら failure_type=error。"""

        class FailStore:
            def search(self, q, top_k=20):
                raise RuntimeError("connection error")

        runner = RAGQualityRunner(store=FailStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.passed is False
        assert result.failure_type == "error"
        assert result.failure_category == "tool_failure"

    def test_empty_search_results(self, s1_case):
        class EmptyStore:
            def search(self, q, top_k=20):
                return []

        runner = RAGQualityRunner(store=EmptyStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert "検索結果がありません" in result.answer


class TestRunAll:
    def test_run_all_returns_eval_run(self, s1_case, s2_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        run = runner.run_all([s1_case, s2_case], run_id="test-001")
        assert isinstance(run, EvalRun)
        assert run.run_id == "test-001"
        assert run.total == 2

    def test_run_all_auto_id(self, s1_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        run = runner.run_all([s1_case])
        assert run.run_id  # non-empty


class TestSaveJsonl:
    def test_save_and_read(self, tmp_path, s1_case, s2_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        run = runner.run_all([s1_case, s2_case])
        jsonl_path = RAGQualityRunner.save_jsonl(run, [s1_case, s2_case], str(tmp_path / "logs"))
        assert jsonl_path.exists()
        lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2

    def test_save_creates_dir(self, tmp_path, s1_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        run = runner.run_all([s1_case])
        log_dir = tmp_path / "new" / "nested"
        jsonl_path = RAGQualityRunner.save_jsonl(run, [s1_case], str(log_dir))
        assert jsonl_path.exists()
