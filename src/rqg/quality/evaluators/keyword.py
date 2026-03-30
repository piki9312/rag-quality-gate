"""Keyword 評価 — 回答に期待キーワードが含まれるかを検証。"""

from __future__ import annotations


def _split_or_terms(keyword_spec: str) -> list[str]:
    """Split one keyword spec by OR token (`|`) and normalize each term."""
    return [term.strip().lower() for term in keyword_spec.split("|") if term.strip()]


def keyword_match_rate(answer: str, expected_keywords: list[str]) -> float:
    """expected_keywords のうち回答に含まれるものの割合 (0.0〜1.0)。

    `expected_keywords` の各要素で `|` を使うと OR 条件として扱う。
    例: `期限|5営業日前` はどちらかが回答に含まれていれば一致。
    """
    if not expected_keywords:
        return 1.0

    answer_lower = answer.lower()
    specs = [_split_or_terms(spec) for spec in expected_keywords]
    valid_specs = [terms for terms in specs if terms]
    if not valid_specs:
        return 1.0

    hits = sum(1 for terms in valid_specs if any(term in answer_lower for term in terms))
    return hits / len(valid_specs)
