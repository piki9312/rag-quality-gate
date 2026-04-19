"""Tests for LLM-as-Judge evaluator."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from rqg.quality.evaluators.llm_judge import (
    _JUDGE_SYSTEM,
    JudgeResult,
    _mock_judge,
    _parse_judge_response,
    judge,
)

# ==================================================================
# _parse_judge_response
# ==================================================================


class TestParseJudgeResponse:
    def test_valid_json(self):
        text = '{"faithfulness": 0.9, "relevance": 0.8, "reasoning": "well grounded"}'
        f, r, reason = _parse_judge_response(text)
        assert f == 0.9
        assert r == 0.8
        assert reason == "well grounded"

    def test_json_with_markdown_fences(self):
        text = '```json\n{"faithfulness": 0.7, "relevance": 0.6, "reasoning": "ok"}\n```'
        f, r, reason = _parse_judge_response(text)
        assert f == 0.7
        assert r == 0.6

    def test_clamps_out_of_range(self):
        text = '{"faithfulness": 1.5, "relevance": -0.3, "reasoning": "clamped"}'
        f, r, _ = _parse_judge_response(text)
        assert f == 1.0
        assert r == 0.0

    def test_missing_fields_default_zero(self):
        text = '{"faithfulness": 0.5}'
        f, r, reason = _parse_judge_response(text)
        assert f == 0.5
        assert r == 0.0
        assert reason == ""

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_judge_response("not json")


# ==================================================================
# _mock_judge
# ==================================================================


class TestMockJudge:
    def test_empty_answer(self):
        result = _mock_judge("質問", "", "コンテキスト")
        assert result.faithfulness == 0.0
        assert result.relevance == 0.0

    def test_high_overlap_with_context(self):
        context = "有給休暇は5営業日前までに申請してください"
        answer = "有給休暇は5営業日前までに申請してください"
        result = _mock_judge("有給休暇", answer, context)
        assert result.faithfulness > 0.5

    def test_no_context(self):
        result = _mock_judge("質問", "何か回答", "")
        assert result.faithfulness == 0.0

    def test_returns_judge_result(self):
        result = _mock_judge("q", "a b c", "a b c d")
        assert isinstance(result, JudgeResult)
        assert "mock" in result.reasoning

    def test_japanese_overlap_scores_relevance_without_whitespace(self):
        result = _mock_judge(
            "有給休暇の申請期限は？",
            "有給休暇は5営業日前までに申請しなければならない。",
            "有給休暇は5営業日前までに申請しなければならない。",
        )
        assert result.faithfulness >= 0.7
        assert result.relevance >= 0.2

    def test_japanese_relevance_uses_best_matching_sentence(self):
        answer = (
            "経費精算の締め日は毎月25日です。\n" "有給休暇は5営業日前までに申請しなければならない。"
        )
        context = answer
        result = _mock_judge("有給休暇の申請期限は？", answer, context)
        assert result.relevance >= 0.2


class TestJudgePrompt:
    def test_prompt_reserves_perfect_scores_for_complete_answers(self):
        assert "1.0 is rare" in _JUDGE_SYSTEM
        assert "no material requested detail is missing" in _JUDGE_SYSTEM

    def test_prompt_penalizes_partial_and_heading_answers(self):
        assert "section heading" in _JUDGE_SYSTEM
        assert "introductory sentence is not complete" in _JUDGE_SYSTEM
        assert "enumerated or list-style question" in _JUDGE_SYSTEM


# ==================================================================
# judge() — mock mode
# ==================================================================


class TestJudgeMock:
    def test_mock_mode_no_llm_call(self):
        result = judge(
            question="有給休暇の申請期限は？",
            answer="5営業日前までに申請してください。",
            context="有給休暇は5営業日前までに申請が必要です。",
            mock=True,
        )
        assert isinstance(result, JudgeResult)
        assert 0.0 <= result.faithfulness <= 1.0
        assert 0.0 <= result.relevance <= 1.0
        assert result.usage is None

    def test_mock_empty_answer(self):
        result = judge(question="q", answer="", context="ctx", mock=True)
        assert result.faithfulness == 0.0


# ==================================================================
# judge() — LLM mode (mocked OpenAI)
# ==================================================================


class TestJudgeLLM:
    def test_successful_llm_call(self):
        mock_response = {
            "text": '{"faithfulness": 0.95, "relevance": 0.9, "reasoning": "well grounded"}',
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "estimated_cost_usd": 0.0001,
            },
        }
        with patch(
            "rqg.serving.llm_client.call_openai_chat",
            return_value=mock_response,
        ) as mock_call:
            result = judge(
                question="有給休暇の申請期限は？",
                answer="5営業日前までに申請してください。",
                context="有給休暇は5営業日前までに申請が必要です。",
                mock=False,
            )
            mock_call.assert_called_once()
            assert result.faithfulness == 0.95
            assert result.relevance == 0.9
            assert result.usage is not None
            assert result.usage["input_tokens"] == 100

    def test_custom_model(self):
        mock_response = {
            "text": '{"faithfulness": 0.8, "relevance": 0.7, "reasoning": "ok"}',
            "usage": {},
        }
        with patch(
            "rqg.serving.llm_client.call_openai_chat",
            return_value=mock_response,
        ) as mock_call:
            judge(
                question="q",
                answer="a",
                context="c",
                mock=False,
                model="gpt-4o",
            )
            args = mock_call.call_args
            assert args[1]["model"] == "gpt-4o" or args[0][0] == "gpt-4o"

    def test_parse_error_falls_back_to_mock(self):
        mock_response = {"text": "INVALID JSON !!!", "usage": {}}
        with patch(
            "rqg.serving.llm_client.call_openai_chat",
            return_value=mock_response,
        ):
            result = judge(question="q", answer="a b c", context="a b c d", mock=False)
            assert isinstance(result, JudgeResult)
            assert "mock" in result.reasoning
            assert result.fallback_used is True
            assert result.fallback_reason == "parse_error"

    def test_api_error_falls_back_to_mock(self):
        with patch(
            "rqg.serving.llm_client.call_openai_chat",
            side_effect=RuntimeError("API down"),
        ):
            result = judge(question="q", answer="a b c", context="a b c d", mock=False)
            assert isinstance(result, JudgeResult)
            assert "mock" in result.reasoning
            assert result.fallback_used is True
            assert result.fallback_reason == "api_error"

    def test_successful_call_no_fallback(self):
        mock_response = {
            "text": '{"faithfulness": 0.9, "relevance": 0.8, "reasoning": "ok"}',
            "usage": {},
        }
        with patch(
            "rqg.serving.llm_client.call_openai_chat",
            return_value=mock_response,
        ):
            result = judge(question="q", answer="a", context="a", mock=False)
            assert result.fallback_used is False
            assert result.fallback_reason is None

    def test_mock_mode_no_fallback(self):
        result = judge(question="q", answer="a b", context="a b c", mock=True)
        assert result.fallback_used is False
        assert result.fallback_reason is None


# ==================================================================
# Integration: judge score in runner (via mock)
# ==================================================================


class TestJudgeInRunner:
    """RAGQualityRunner が faithfulness_score を返すことを確認。"""

    def test_mock_runner_has_faithfulness(self, s1_case):
        from rqg.quality.runner import RAGQualityRunner

        class FakeStore:
            def search(self, query, top_k=20):
                return [
                    {"chunk_id": "chunk_A", "text": "5営業日前までに申請してください。"},
                    {"chunk_id": "chunk_B", "text": "25日が締め日です。"},
                ]

        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        assert result.faithfulness_score is not None
        assert result.judge_relevance is not None
        assert result.evidence_recall == 1.0
        assert 0.0 <= result.faithfulness_score <= 1.0

    def test_empty_retrieval_no_faithfulness(self, s1_case):
        from rqg.quality.runner import RAGQualityRunner

        class EmptyStore:
            def search(self, q, top_k=20):
                return []

        runner = RAGQualityRunner(store=EmptyStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        # No retrieved chunks = no judge call
        assert result.faithfulness_score is None

    def test_faithfulness_in_jsonl_record(self, s1_case):
        from rqg.quality.models import QARunRecord
        from rqg.quality.runner import RAGQualityRunner

        class FakeStore:
            def search(self, query, top_k=20):
                return [{"chunk_id": "chunk_A", "text": "5営業日前までに申請してください。"}]

        runner = RAGQualityRunner(store=FakeStore(), mock_llm=True)
        result = runner.run_case(s1_case)
        record = QARunRecord.from_eval_result(result, "run-001", s1_case)
        assert record.faithfulness_score == result.faithfulness_score
        assert record.judge_relevance == result.judge_relevance
        assert record.evidence_recall == result.evidence_recall
        # Verify it serializes to JSON
        data = json.loads(record.model_dump_json())
        assert "faithfulness_score" in data
        assert "judge_relevance" in data
        assert "evidence_recall" in data
