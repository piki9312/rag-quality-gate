"""Tests for RAGQualityRunner — mock LLM & mock store でE2E評価。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rqg.quality.evaluators.llm_judge import JudgeResult
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
        # Mock LLM は質問に近い excerpt を返す
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

    def test_mock_llm_prefers_relevant_markdown_section(self):
        class SectionStore:
            def search(self, q, top_k=20):
                return [
                    {
                        "chunk_id": "policy.md#chunk1",
                        "text": "# 就業規則\n\n## 在宅勤務\n\n在宅勤務は週2回まで可能です。\n\n## 有給休暇\n\n有給休暇は5営業日前までに申請し、上長承認を得てください。",
                    }
                ]

        case = QATestCase(
            case_id="QA-section",
            name="section focus",
            question="有給休暇の申請期限は？",
            severity="S1",
            expected_keywords=["5営業日前", "申請"],
            expected_evidence=[],
            category="policy",
        )

        runner = RAGQualityRunner(store=SectionStore(), mock_llm=True)
        result = runner.run_case(case)

        assert "有給休暇" in result.answer
        assert "5営業日前" in result.answer
        assert "在宅勤務は週2回" not in result.answer

    def test_mock_llm_formats_contact_answers(self):
        class ContactStore:
            def search(self, q, top_k=20):
                return [
                    {
                        "chunk_id": "rules.md#chunk1",
                        "text": "# 就業規則\n\n## 在宅勤務\n\n在宅勤務は週2回まで可能です。",
                    },
                    {
                        "chunk_id": "benefits.md#chunk1",
                        "text": "# 福利厚生制度\n\n## 個人情報の取り扱い\n\n従業員の個人情報は、人事部が厳格に管理します。\n業務上必要な場合は情報セキュリティ担当の承認を得ること。",
                    },
                ]

        case = QATestCase(
            case_id="QA-contact",
            name="contact answer",
            question="問い合わせ先はどこですか？",
            severity="S2",
            expected_keywords=["人事部"],
            expected_evidence=[],
            category="escalation",
        )

        runner = RAGQualityRunner(store=ContactStore(), mock_llm=True)
        result = runner.run_case(case)

        assert "問い合わせ先は人事部です" in result.answer
        assert result.passed is True
        assert (result.judge_relevance or 0.0) > 0.0

    def test_mock_llm_matches_receipt_synonym_for_evidence_questions(self):
        class ReceiptStore:
            def search(self, q, top_k=20):
                return [
                    {
                        "chunk_id": "expense.md#chunk1",
                        "text": "# 経費精算ガイドライン\n\n## 1. 締め日と提出方法\n\n25日までにレシート原本を添付の上、経費精算システムから申請してください。\n\n## 4. 接待費\n\n接待費は事前に上長の承認を得てから支出してください。",
                    }
                ]

        case = QATestCase(
            case_id="QA-receipt",
            name="receipt synonym",
            question="経費精算に必要な証憑は何ですか？",
            severity="S2",
            expected_keywords=["レシート", "添付", "経費精算システム"],
            expected_evidence=[],
            category="procedure",
        )

        runner = RAGQualityRunner(store=ReceiptStore(), mock_llm=True)
        result = runner.run_case(case)

        assert "レシート原本" in result.answer
        assert "接待費" not in result.answer
        assert result.passed is True

    def test_mock_llm_prioritizes_exact_topic_over_generic_procedure_terms(self):
        class OvertimeStore:
            def search(self, q, top_k=20):
                return [
                    {
                        "chunk_id": "rules.md#chunk1",
                        "text": "# 就業規則\n\n## 残業\n\n残業を行う場合は、事前に上司へ残業申請を行い、承認を得なければならない。\n\n## 接待費\n\n接待費は事前に上長の承認を得てから支出してください。",
                    }
                ]

        case = QATestCase(
            case_id="QA-overtime",
            name="overtime topic",
            question="残業をする場合の事前申請手順は何ですか？",
            severity="S2",
            expected_keywords=["残業申請", "上司", "承認"],
            expected_evidence=[],
            category="procedure",
        )

        runner = RAGQualityRunner(store=OvertimeStore(), mock_llm=True)
        result = runner.run_case(case)

        assert "残業" in result.answer
        assert "接待費" not in result.answer
        assert result.passed is True


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
        assert rows[0]["evidence_recall"] == 1.0
        assert rows[0]["judge_relevance"] is not None
        assert rows[1]["answer_match"] is True
        assert rows[1]["evidence_match"] is None
        assert rows[1]["evidence_recall"] is None

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


class TestRunCaseEvalMode:
    def test_exact_mode_uses_expected_answer(self):
        class ExactStore:
            def search(self, q, top_k=20):
                return [{"chunk_id": "chunk_A", "text": "有給休暇は5営業日前までに申請してください。"}]

        case = QATestCase(
            case_id="EXACT-001",
            name="exact mode",
            question="有給申請の期限は？",
            severity="S1",
            eval_mode="exact",
            expected_answer="有給休暇は5営業日前までに申請してください。",
            expected_keywords=["存在しないキーワード"],
            expected_evidence=["chunk_A"],
        )

        runner = RAGQualityRunner(store=ExactStore(), mock_llm=True)
        result = runner.run_case(case)

        assert result.passed is True
        assert result.answer_match is True
        assert result.failure_type is None

    def test_exact_mode_fails_when_expected_answer_differs(self):
        class ExactStore:
            def search(self, q, top_k=20):
                return [{"chunk_id": "chunk_A", "text": "有給休暇は5営業日前までに申請してください。"}]

        case = QATestCase(
            case_id="EXACT-002",
            name="exact mismatch",
            question="有給申請の期限は？",
            severity="S1",
            eval_mode="exact",
            expected_answer="有給休暇は3営業日前までに申請してください。",
            expected_evidence=["chunk_A"],
        )

        runner = RAGQualityRunner(store=ExactStore(), mock_llm=True)
        result = runner.run_case(case)

        assert result.passed is False
        assert result.answer_match is False
        assert result.failure_type == "keyword_miss"

    def test_evidence_keyword_mode_requires_both_metrics(self):
        case = QATestCase(
            case_id="EK-001",
            name="evidence keyword pass",
            question="経費精算の締め日は？",
            severity="S2",
            eval_mode="evidence_keyword",
            expected_keywords=["25日", "レシート"],
            expected_evidence=["chunk_B", "chunk_X"],
        )

        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(case)

        assert result.passed is True
        assert result.answer_match is True
        assert result.evidence_match is True
        assert result.evidence_recall == pytest.approx(0.5)

    def test_evidence_keyword_mode_fails_on_evidence_recall(self):
        case = QATestCase(
            case_id="EK-002",
            name="evidence keyword miss",
            question="経費精算の締め日は？",
            severity="S2",
            eval_mode="evidence_keyword",
            expected_keywords=["25日", "レシート"],
            expected_evidence=["chunk_Z"],
        )

        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(case)

        assert result.passed is False
        assert result.answer_match is True
        assert result.evidence_match is False
        assert result.evidence_recall == 0.0
        assert result.failure_type == "retrieval_miss"

    def test_grounded_judge_mode_requires_citation_and_judge_scores(self):
        class GroundedStore:
            def search(self, q, top_k=20):
                return [{"chunk_id": "doc#chunk1", "text": "有給休暇は5営業日前までに申請してください。"}]

        case = QATestCase(
            case_id="GJ-001",
            name="grounded judge",
            question="有給申請の期限は？",
            severity="S1",
            eval_mode="grounded_judge",
            expected_evidence=["doc#chunk1"],
        )

        with (
            patch(
                "rqg.quality.runner.generate_answer",
                return_value=("有給休暇は5営業日前までに申請してください。[doc#chunk1]", {"usage": {}}),
            ),
            patch(
                "rqg.quality.runner.llm_judge",
                return_value=JudgeResult(
                    faithfulness=0.95,
                    relevance=0.92,
                    reasoning="grounded",
                ),
            ),
        ):
            runner = RAGQualityRunner(store=GroundedStore(), mock_llm=False)
            result = runner.run_case(case)

        assert result.passed is True
        assert result.answer_match is True
        assert result.evidence_match is True
        assert result.evidence_recall == 1.0
        assert result.judge_relevance == 0.92
        assert result.failure_type is None

    def test_grounded_judge_mode_passes_with_mock_citations(self):
        class GroundedMockStore:
            def search(self, q, top_k=20):
                return [
                    {
                        "chunk_id": "policy.md#chunk1",
                        "text": "Employees must submit a temporary VPN exception request through the IT service portal with manager approval.",
                    }
                ]

        case = QATestCase(
            case_id="GJ-003",
            name="grounded judge mock",
            question="How should employees submit a temporary VPN exception request?",
            severity="S2",
            eval_mode="grounded_judge",
            expected_evidence=["policy.md#chunk1"],
        )

        runner = RAGQualityRunner(store=GroundedMockStore(), mock_llm=True)
        result = runner.run_case(case)

        assert "[policy.md#chunk1]" in result.answer
        assert result.passed is True
        assert result.evidence_match is True
        assert result.judge_relevance is not None
        assert result.failure_type is None

    def test_grounded_judge_mode_fails_without_citation(self):
        class GroundedStore:
            def search(self, q, top_k=20):
                return [{"chunk_id": "doc#chunk1", "text": "有給休暇は5営業日前までに申請してください。"}]

        case = QATestCase(
            case_id="GJ-002",
            name="grounded judge no citation",
            question="有給申請の期限は？",
            severity="S1",
            eval_mode="grounded_judge",
            expected_evidence=["doc#chunk1"],
        )

        with (
            patch(
                "rqg.quality.runner.generate_answer",
                return_value=("有給休暇は5営業日前までに申請してください。", {"usage": {}}),
            ),
            patch(
                "rqg.quality.runner.llm_judge",
                return_value=JudgeResult(
                    faithfulness=0.95,
                    relevance=0.92,
                    reasoning="grounded",
                ),
            ),
        ):
            runner = RAGQualityRunner(store=GroundedStore(), mock_llm=False)
            result = runner.run_case(case)

        assert result.passed is False
        assert result.answer_match is True
        assert result.evidence_match is True
        assert result.evidence_recall == 1.0
        assert result.judge_relevance == 0.92
        assert result.failure_type == "bad_reference"

    def test_grounded_judge_uses_rollout_threshold(self):
        class GroundedStore:
            def search(self, q, top_k=20):
                return [{"chunk_id": "doc#chunk1", "text": "有給休暇は5営業日前までに申請してください。"}]

        case = QATestCase(
            case_id="GJ-004",
            name="grounded rollout threshold",
            question="有給申請の期限は？",
            severity="S1",
            eval_mode="grounded_judge",
            expected_evidence=["doc#chunk1"],
        )

        with (
            patch(
                "rqg.quality.runner.generate_answer",
                return_value=("有給休暇は5営業日前までに申請してください。[doc#chunk1]", {"usage": {}}),
            ),
            patch(
                "rqg.quality.runner.llm_judge",
                return_value=JudgeResult(
                    faithfulness=0.55,
                    relevance=0.52,
                    reasoning="grounded",
                ),
            ),
        ):
            runner = RAGQualityRunner(store=GroundedStore(), mock_llm=False)
            result = runner.run_case(case)

        assert result.passed is True
        assert result.failure_type is None


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
    """legacy score は keyword/references/judge の平均。"""

    def test_score_with_full_keyword_match(self, s1_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        expected = (1.0 + 1.0 + (result.faithfulness_score or 0.0)) / 3
        assert result.score == pytest.approx(expected)


class TestJudgeFallbackRecording:
    """Runner が JudgeResult の fallback 情報を EvalResult / QARunRecord に伝搬する。"""

    def test_mock_mode_no_fallback(self, s1_case):
        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.judge_fallback_used is False
        assert result.judge_fallback_reason is None

    def test_fallback_propagated_to_jsonl_record(self, s1_case):
        """parse_error フォールバック時に QARunRecord にも記録される。"""
        from rqg.quality.models import QARunRecord

        mock_llm_response = {"text": "NOT JSON", "usage": {}}
        mock_answer_meta = {"usage": {}}

        with (
            patch(
                "rqg.quality.runner.generate_answer",
                return_value=("5営業日前 申請 回答テスト", mock_answer_meta),
            ),
            patch(
                "rqg.serving.llm_client.call_openai_chat",
                return_value=mock_llm_response,
            ),
        ):
            runner = RAGQualityRunner(store=FakeStore(), mock_llm=False)
            result = runner.run_case(s1_case)

        assert result.judge_fallback_used is True
        assert result.judge_fallback_reason == "parse_error"

        record = QARunRecord.from_eval_result(result, "run-fb", s1_case)
        assert record.judge_fallback_used is True
        assert record.judge_fallback_reason == "parse_error"
        data = json.loads(record.model_dump_json())
        assert data["judge_fallback_used"] is True
        assert data["judge_fallback_reason"] == "parse_error"
