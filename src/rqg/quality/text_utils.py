"""共通テキストユーティリティ — 正規化・トークン化・重複率計算。

llm_judge と runner の両方で使われる関数を集約。
"""

from __future__ import annotations

import re
import unicodedata

_TOKEN_RE = re.compile(r"[a-z0-9]+|[ぁ-んァ-ヶー一-龠々〆ヵヶ]+", re.IGNORECASE)
_ASCII_TOKEN_RE = re.compile(r"^[a-z0-9]+$", re.IGNORECASE)


def normalize_text(text: str) -> str:
    """NFKC 正規化 + 小文字化 + 空白統一。"""
    normalized = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"\s+", " ", normalized).strip()


def overlap_tokens(text: str) -> set[str]:
    """テキストからトークン集合を抽出する（日本語は bi/tri-gram）。"""
    normalized = normalize_text(text)
    tokens: set[str] = set()
    for piece in _TOKEN_RE.findall(normalized):
        if not piece:
            continue
        if _ASCII_TOKEN_RE.match(piece):
            tokens.add(piece)
            continue

        if len(piece) <= 2:
            tokens.add(piece)
            continue

        for n in (2, 3):
            if len(piece) < n:
                continue
            for idx in range(len(piece) - n + 1):
                tokens.add(piece[idx : idx + n])

        if len(piece) <= 8:
            tokens.add(piece)
    return tokens


def split_text_units(text: str) -> list[str]:
    """テキストを文単位に分割する。"""
    normalized = unicodedata.normalize("NFKC", text).lower()
    segments = re.split(r"[。！？.!?]+|\r?\n+", normalized)
    return [re.sub(r"\s+", " ", segment).strip() for segment in segments if segment.strip()]


def overlap_precision(reference_tokens: set[str], candidate_tokens: set[str]) -> float:
    """candidate のうち reference に含まれるトークンの割合。"""
    if not reference_tokens or not candidate_tokens:
        return 0.0
    overlap = len(reference_tokens & candidate_tokens)
    return overlap / len(candidate_tokens)


def overlap_f1(reference_tokens: set[str], candidate_tokens: set[str]) -> float:
    """reference と candidate のトークン F1 スコア。"""
    if not reference_tokens or not candidate_tokens:
        return 0.0

    overlap = len(reference_tokens & candidate_tokens)
    if overlap == 0:
        return 0.0

    precision = overlap / len(candidate_tokens)
    recall = overlap / len(reference_tokens)
    return (2 * precision * recall) / (precision + recall)
