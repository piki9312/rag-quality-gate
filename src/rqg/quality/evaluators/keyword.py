"""Keyword 評価 — 回答に期待キーワードが含まれるかを検証。"""

from __future__ import annotations


def keyword_match_rate(answer: str, expected_keywords: list[str]) -> float:
    """expected_keywords のうち回答に含まれるものの割合 (0.0〜1.0)。"""
    if not expected_keywords:
        return 1.0
    answer_lower = answer.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return hits / len(expected_keywords)
