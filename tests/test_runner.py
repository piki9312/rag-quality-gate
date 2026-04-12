"""Tests for RAGQualityRunner — mock LLM & mock store でE2E評価。"""

from __future__ import annotations

import json
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
        assert result.answer_match is True
        assert result.evidence_match is True

    def test_s2_pass_mock_llm(self, s2_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s2_case)
        assert result.case_id == "QA002"
        # "25日" と "レシート" が結合テキストに含まれるはず
        assert "25日" in result.answer
        assert result.answer_match is True
        assert result.evidence_match is None

    def test_retrieval_hit_detected(self, s1_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.retrieval_hit is True  # chunk_A が返ってくる

    def test_retrieval_miss(self, s1_case):
        s1_case.expected_evidence = ["chunk_X"]
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.retrieval_hit is False
        assert result.answer_match is True
        assert result.evidence_match is False
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
        assert result.answer_match is None
        assert result.evidence_match is None

    def test_empty_search_results(self, s1_case):
        class EmptyStore:
            def search(self, q, top_k=20):
                return []

        runner = RAGQualityRunner(store=EmptyStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert "検索結果がありません" in result.answer

    def test_mock_llm_keeps_tail_keywords(self):
        class LongTailStore:
            def search(self, q, top_k=20):
                return [{"chunk_id": "chunk_tail", "text": "x" * 140 + " on-call"}]

        case = QATestCase(
            case_id="QA-tail",
            name="tail keyword",
            question="Who is the escalation owner?",
            severity="S2",
            expected_keywords=["on-call"],
            expected_evidence=[],
            category="escalation",
        )

        runner = RAGQualityRunner(store=LongTailStore(), mock_llm=True)
        result = runner.run_case(case)
        assert result.passed is True
        assert "on-call" in result.answer


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
        rows = [json.loads(line) for line in lines]
        assert rows[0]["answer_match"] is True
        assert rows[0]["evidence_match"] is True
        assert rows[1]["answer_match"] is True
        assert rows[1]["evidence_match"] is None

    def test_save_creates_dir(self, tmp_path, s1_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        run = runner.run_all([s1_case])
        log_dir = tmp_path / "new" / "nested"
        jsonl_path = RAGQualityRunner.save_jsonl(run, [s1_case], str(log_dir))
        assert jsonl_path.exists()


# ------------------------------------------------------------------
# run_case unit tests — edge cases & evaluation paths
# ------------------------------------------------------------------


class TestRunCaseKeywordMiss:
    """keyword_match_rate が閾値を下回る場合。"""

    def test_s1_keyword_miss(self):
        """S1 は 80% 未満で keyword_miss。"""

        class PartialStore:
            def search(self, q, top_k=20):
                # "5営業日前" は入るが "上長承認" は入らない
                return [{"chunk_id": "c1", "text": "5営業日前までに申請。"}]

        case = QATestCase(
            case_id="KW-S1",
            name="keyword miss S1",
            question="有給申請の手順は？",
            severity="S1",
            expected_keywords=["5営業日前", "上長承認", "人事部"],
            expected_evidence=[],
        )
        runner = RAGQualityRunner(store=PartialStore(), mock_llm=True)
        result = runner.run_case(case)
        # 1/3 = 33% < 80% → fail
        assert result.passed is False
        assert result.failure_type == "keyword_miss"
        assert result.answer_match is False

    def test_s2_keyword_threshold_is_lower(self):
        """S2 は 50% で OK — 2/3 ≈ 67% > 50%。"""

        class TwoHitStore:
            def search(self, q, top_k=20):
                return [{"chunk_id": "c1", "text": "25日が締め日。レシートを添付して提出。"}]

        case = QATestCase(
            case_id="KW-S2",
            name="keyword threshold S2",
            question="経費精算の締め日は？",
            severity="S2",
            expected_keywords=["25日", "レシート", "部長承認"],
            expected_evidence=[],
        )
        runner = RAGQualityRunner(store=TwoHitStore(), mock_llm=True)
        result = runner.run_case(case)
        # 2/3 ≈ 67% >= 50% → pass
        assert result.passed is True
        assert result.answer_match is True


class TestRunCaseDedup:
    """検索結果の重複排除と context_k 上限。"""

    def test_duplicate_chunks_are_removed(self, s1_case):
        class DupStore:
            def search(self, q, top_k=20):
                return [
                    {"chunk_id": "chunk_A", "text": "5営業日前までに申請。"},
                    {"chunk_id": "chunk_A", "text": "5営業日前までに申請。"},
                    {"chunk_id": "chunk_B", "text": "上長の承認が必要。"},
                ]

        runner = RAGQualityRunner(store=DupStore(), mock_llm=True, context_k=5)
        result = runner.run_case(s1_case)
        # chunk_A の重複は除去されて 2 件になる
        assert result.retrieved_ids == ["chunk_A", "chunk_B"]

    def test_context_k_limits_results(self, s1_case):
        class ManyStore:
            def search(self, q, top_k=20):
                return [{"chunk_id": f"c{i}", "text": f"text{i}"} for i in range(10)]

        runner = RAGQualityRunner(store=ManyStore(), mock_llm=True, context_k=3)
        result = runner.run_case(s1_case)
        assert len(result.retrieved_ids) == 3


class TestRunCaseMultiSearch:
    """use_multi=True で search_multi が呼ばれる。"""

    def test_use_multi_calls_search_multi(self, s1_case):
        class MultiStore:
            def __init__(self):
                self.called_multi = False

            def search(self, q, top_k=20):
                raise AssertionError("search should not be called")

            def search_multi(self, q, top_k=20):
                self.called_multi = True
                return [{"chunk_id": "chunk_A", "text": "5営業日前 申請"}]

        store = MultiStore()
        runner = RAGQualityRunner(store=store, mock_llm=True, use_multi=True)
        result = runner.run_case(s1_case)
        assert store.called_multi is True
        assert result.retrieved_ids == ["chunk_A"]


class TestRunCaseSpecificExceptions:
    """具体例外型のみキャッチされることを確認。"""

    def test_value_error_caught(self, s1_case):
        class BadStore:
            def search(self, q, top_k=20):
                raise ValueError("bad embedding dimension")

        runner = RAGQualityRunner(store=BadStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.passed is False
        assert result.failure_type == "error"
        assert "bad embedding dimension" in result.failure_reason

    def test_os_error_caught(self, s1_case):
        class DiskStore:
            def search(self, q, top_k=20):
                raise OSError("disk read failure")

        runner = RAGQualityRunner(store=DiskStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.passed is False
        assert result.failure_type == "error"

    def test_unexpected_exception_propagates(self, s1_case):
        """キャッチ対象外の例外は握りつぶさず伝播する。"""

        class WeirdStore:
            def search(self, q, top_k=20):
                raise SystemExit("should propagate")

        runner = RAGQualityRunner(store=WeirdStore(), mock_llm=True)
        with pytest.raises(SystemExit):
            runner.run_case(s1_case)


class TestRunCaseScoreCalculation:
    """score は keyword_match_rate と reference_accuracy の平均。"""

    def test_score_with_full_keyword_match(self, s1_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        # keywords: "5営業日前" + "申請" → 2/2 = 100%
        # reference_accuracy: no refs in mock answer → 100%
        # average: 100%
        assert result.score == pytest.approx(1.0)
