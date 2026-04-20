"""LLM-as-Judge 評価 — LLM で faithfulness / answer relevance を判定。"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from ..text_utils import (
    overlap_f1,
    overlap_precision,
    overlap_tokens,
    split_text_units,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass
class JudgeResult:
    """LLM Judge の判定結果。"""

    faithfulness: float  # 0.0〜1.0
    relevance: float  # 0.0〜1.0
    reasoning: str = ""
    usage: dict[str, Any] | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = (
    "You are a strict, conservative quality evaluator for a RAG (Retrieval-Augmented Generation) system.\n"
    "Score the ANSWER against the QUESTION and CONTEXT only.\n"
    "Use the full score range and prefer conservative grading. When unsure, choose the lower score.\n\n"
    "You must evaluate the ANSWER on two axes:\n"
    "1. **Faithfulness** (0.0-1.0): Is the answer grounded in the provided CONTEXT? "
    "1.0 = every material claim is explicitly supported by the context with no unsupported additions. "
    "0.0 = the answer is contradicted by the context, fabricated, or effectively unsupported.\n"
    "2. **Relevance** (0.0-1.0): Does the answer directly and sufficiently address the QUESTION? "
    "1.0 = complete, direct, and audit-ready answer to the whole question. "
    "0.0 = completely off-topic, empty, or unhelpful.\n\n"
    "Scoring rubric:\n"
    "- 1.0 is rare. Use it only when the answer completely resolves the whole question and no material requested detail is missing.\n"
    "- 0.8-0.95: strongly useful and mostly complete, but slightly compressed, indirect, or missing minor detail.\n"
    "- 0.5-0.75: partially answers the question, gives only one aspect of a multi-part ask, or requires reader inference.\n"
    "- 0.1-0.45: related snippet, heading, label, lead-in sentence, or vague statement that does not actually answer the question.\n"
    "- 0.0: off-topic, empty, contradictory, or unsupported.\n\n"
    "Apply these conservative rules:\n"
    "- If the question asks for a procedure, conditions, exceptions, list of reasons, list of steps, or contact order, an answer that gives only one fact or only the introductory sentence is not complete.\n"
    "- If the answer only repeats a section heading, document title, label, or citation, relevance must be very low.\n"
    "- If the answer omits requested items from an enumerated or list-style question, relevance should usually stay at or below 0.6.\n"
    "- Do not award 1.0 when the reader must infer the requested target from a merely related sentence.\n"
    "- A short fact answer can still score high, but reserve 1.0 for cases where it fully answers exactly what was asked.\n"
    "- Do not reward answers for sounding plausible; judge only what is explicitly supported by the CONTEXT.\n\n"
    "Respond with ONLY a JSON object:\n"
    '{"faithfulness": <float>, "relevance": <float>, "reasoning": "<brief explanation>"}\n'
    "No markdown, no extra text."
)

_JUDGE_USER_TEMPLATE = "CONTEXT:\n{context}\n\n" "QUESTION:\n{question}\n\n" "ANSWER:\n{answer}"


# ---------------------------------------------------------------------------
# Mock judge (テスト/CI 用)
# ---------------------------------------------------------------------------


def _mock_judge(question: str, answer: str, context: str) -> JudgeResult:
    """Mock 判定 — コンテキストとの単純な重複率で近似スコアを返す。"""
    if not answer.strip():
        return JudgeResult(faithfulness=0.0, relevance=0.0, reasoning="empty answer")

    ctx_words = overlap_tokens(context)
    ans_words = overlap_tokens(answer)
    q_words = overlap_tokens(question)

    if ctx_words and ans_words:
        faithfulness = min(round(overlap_precision(ctx_words, ans_words), 2), 1.0)
    else:
        faithfulness = 0.0

    if q_words:
        answer_segments = _split_text_units(answer)
        segment_scores = [
            _overlap_f1(q_words, _overlap_tokens(segment)) for segment in answer_segments
        ]
        if not segment_scores:
            segment_scores = [overlap_f1(q_words, ans_words)]
        relevance = min(round(max(segment_scores), 2), 1.0)
    else:
        relevance = 0.5

    return JudgeResult(
        faithfulness=faithfulness,
        relevance=relevance,
        reasoning="mock judge (multilingual token overlap heuristic)",
    )


# ---------------------------------------------------------------------------
# LLM judge (OpenAI)
# ---------------------------------------------------------------------------


def _parse_judge_response(text: str) -> tuple[float, float, str]:
    """LLM 応答の JSON をパースしてスコアを抽出する。"""
    text = text.strip()
    # Strip possible markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    data = json.loads(text)
    faithfulness = float(data.get("faithfulness", 0.0))
    relevance = float(data.get("relevance", 0.0))
    reasoning = str(data.get("reasoning", ""))

    # Clamp to [0, 1]
    faithfulness = max(0.0, min(1.0, faithfulness))
    relevance = max(0.0, min(1.0, relevance))
    return faithfulness, relevance, reasoning


def judge(
    question: str,
    answer: str,
    context: str,
    *,
    mock: bool = False,
    model: str | None = None,
) -> JudgeResult:
    """LLM-as-Judge で faithfulness / relevance を評価する。

    Parameters
    ----------
    question : str
        ユーザーの質問。
    answer : str
        RAG システムの回答。
    context : str
        検索で取得したコンテキスト（chunk 結合テキスト）。
    mock : bool
        True の場合 LLM を呼ばす簡易ヒューリスティックで近似する。
    model : str | None
        OpenAI モデル名。None の場合は環境変数 OPENAI_MODEL のデフォルト。
    """
    if mock:
        return _mock_judge(question, answer, context)

    from ...serving.llm_client import OPENAI_MODEL, call_openai_chat

    use_model = model or OPENAI_MODEL
    user_msg = _JUDGE_USER_TEMPLATE.format(
        context=context,
        question=question,
        answer=answer,
    )

    try:
        result = call_openai_chat(
            model=use_model,
            system=_JUDGE_SYSTEM,
            user_msg=user_msg,
            max_tokens=256,
        )
        faithfulness, relevance, reasoning = _parse_judge_response(result["text"])
        return JudgeResult(
            faithfulness=faithfulness,
            relevance=relevance,
            reasoning=reasoning,
            usage=result.get("usage"),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning("LLM judge parse error: %s — falling back to mock", exc)
        result = _mock_judge(question, answer, context)
        result.fallback_used = True
        result.fallback_reason = "parse_error"
        return result
    except Exception as exc:
        logger.warning("LLM judge call failed: %s — falling back to mock", exc)
        result = _mock_judge(question, answer, context)
        result.fallback_used = True
        result.fallback_reason = "api_error"
        return result
