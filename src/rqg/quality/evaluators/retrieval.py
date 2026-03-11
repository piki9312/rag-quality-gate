"""Retrieval 評価 — expected chunk が検索結果 top-k に含まれるかを検証。"""

from __future__ import annotations


def retrieval_hit(retrieved_ids: list[str], expected_chunks: list[str]) -> bool:
    """expected_chunks のうち1つでも retrieved_ids に含まれれば True。"""
    if not expected_chunks:
        return True  # 期待 chunk が未定義なら常に hit
    return any(ec in retrieved_ids for ec in expected_chunks)


def retrieval_precision_at_k(
    retrieved_ids: list[str], expected_chunks: list[str]
) -> float:
    """Precision@k: top-k の中に expected chunk が何割含まれるか。"""
    if not expected_chunks:
        return 1.0
    hits = sum(1 for ec in expected_chunks if ec in retrieved_ids)
    return hits / len(expected_chunks)
