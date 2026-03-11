"""Reference 評価 — 回答中の chunk_id 引用が実在するかを検証。"""

from __future__ import annotations

import re


def extract_references(answer: str) -> list[str]:
    """回答テキストから [chunk_id] 形式の引用を抽出する。"""
    return re.findall(r"\[([^\]]*#chunk\d+)\]", answer)


def reference_accuracy(answer: str, retrieved_ids: list[str]) -> float:
    """回答中の引用のうち、実際に検索結果に存在するものの割合。"""
    refs = extract_references(answer)
    if not refs:
        return 1.0  # 引用なし = 検証対象なし
    valid = sum(1 for r in refs if r in retrieved_ids)
    return valid / len(refs)
