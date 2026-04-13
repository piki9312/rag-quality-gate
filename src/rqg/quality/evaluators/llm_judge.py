"""LLM-as-Judge 評価 — LLM で faithfulness / answer relevance を判定。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

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
    "You are a strict quality evaluator for a RAG (Retrieval-Augmented Generation) system.\n"
    "You must evaluate the ANSWER on two axes:\n"
    "1. **Faithfulness** (0.0-1.0): Is the answer grounded in the provided CONTEXT? "
    "1.0 = every claim is supported by the context. "
    "0.0 = the answer contains fabricated information not in the context.\n"
    "2. **Relevance** (0.0-1.0): Does the answer address the QUESTION? "
    "1.0 = fully answers the question. "
    "0.0 = completely off-topic or unhelpful.\n\n"
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

    # 簡易近似: context と answer の共通単語率
    ctx_words = set(context.lower().split())
    ans_words = set(answer.lower().split())
    q_words = set(question.lower().split())

    if ctx_words:
        overlap = len(ans_words & ctx_words) / max(len(ans_words), 1)
        faithfulness = min(round(overlap, 2), 1.0)
    else:
        faithfulness = 0.0

    if q_words:
        q_overlap = len(ans_words & q_words) / max(len(q_words), 1)
        relevance = min(round(q_overlap, 2), 1.0)
    else:
        relevance = 0.5

    return JudgeResult(
        faithfulness=faithfulness,
        relevance=relevance,
        reasoning="mock judge (word overlap heuristic)",
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
