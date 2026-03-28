"""OpenAI API クライアント — 回答生成 + コスト計算。"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from openai import APIError, APITimeoutError, OpenAI, RateLimitError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# モデル別トークン単価 (USD / 1K tokens)
# ---------------------------------------------------------------------------
_COST_PER_1K: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-4": (0.03, 0.06),
    "gpt-3.5-turbo": (0.0005, 0.0015),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    rate = _COST_PER_1K.get(model)
    if rate is None:
        return None
    in_cost, out_cost = rate
    return round(input_tokens / 1000 * in_cost + output_tokens / 1000 * out_cost, 8)


def get_openai_client(env_path: str | None = None) -> OpenAI:
    env_file = Path(env_path) if env_path else Path(__file__).resolve().parents[3] / ".env"
    env = dotenv_values(env_file) if env_file.exists() else {}
    key = (env.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not found in .env or environment")
    return OpenAI(api_key=key, timeout=30.0)


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """エクスポーネンシャルバックオフ付きリトライデコレータ。"""

    def decorator(func):
        import functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    if attempt < max_retries - 1:
                        wait = min(base_delay * (2**attempt), max_delay)
                        logger.warning(
                            "rate limited (attempt %d/%d), waiting %.1fs",
                            attempt + 1,
                            max_retries,
                            wait,
                        )
                        time.sleep(wait)
                    else:
                        raise
                except APITimeoutError as e:
                    if attempt < max_retries - 1:
                        wait = min(base_delay * (2**attempt), max_delay)
                        logger.warning(
                            "timeout (attempt %d/%d), waiting %.1fs", attempt + 1, max_retries, wait
                        )
                        time.sleep(wait)
                    else:
                        raise
                except APIError:
                    raise

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# 回答生成
# ---------------------------------------------------------------------------

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


@retry_with_backoff()
def call_openai_chat(model: str, system: str, user_msg: str, max_tokens: int) -> dict[str, Any]:
    """OpenAI chat.completions を呼び出す。"""
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    input_tokens = resp.usage.prompt_tokens if resp.usage else 0
    output_tokens = resp.usage.completion_tokens if resp.usage else 0
    return {
        "text": resp.choices[0].message.content or "",
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost_usd": estimate_cost(model, input_tokens, output_tokens),
        },
    }


def generate_answer(
    question: str, retrieved_chunks: list[dict], max_new_tokens: int = 256
) -> tuple[str, dict]:
    """検索済み chunk をコンテキストに OpenAI で回答を生成する。"""
    context_parts = []
    for ch in retrieved_chunks:
        context_parts.append(f"[{ch['chunk_id']}] ({ch['source']})\n{ch['text']}")
    context_text = "\n\n".join(context_parts)

    system_prompt = (
        "あなたは社内文書QAです。必ずCONTEXTの内容だけで回答してください。"
        "CONTEXTに根拠がない場合は『文書内に根拠が見つかりません』とだけ答えてください。"
        "根拠に使った箇所は [chunk_id] を文中に引用してください。"
    )
    user_msg = f"CONTEXT:\n\n{context_text}\n\nQUESTION:\n{question}\n"

    result = call_openai_chat(OPENAI_MODEL, system_prompt, user_msg, max_new_tokens)
    meta: dict = {"context_chars": len(context_text), "usage": result["usage"]}
    return result["text"], meta
