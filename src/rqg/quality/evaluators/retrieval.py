"""Retrieval 評価 — expected evidence が検索結果 top-k に含まれるかを検証。"""

from __future__ import annotations

from pathlib import PurePosixPath


def _evidence_aliases(value: str) -> set[str]:
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        return set()

    aliases = {normalized}

    if "@" in normalized:
        aliases.add(normalized.split("@", 1)[0])
    if "#" in normalized:
        aliases.add(normalized.split("#", 1)[0])

    expanded = set(aliases)
    for alias in aliases:
        name = PurePosixPath(alias).name
        if name:
            expanded.add(name)
    return expanded


def _matches_expected_evidence(retrieved_id: str, expected_chunk: str) -> bool:
    return bool(_evidence_aliases(retrieved_id) & _evidence_aliases(expected_chunk))


def retrieval_hit(retrieved_ids: list[str], expected_chunks: list[str]) -> bool:
    """expected_chunks のうち1つでも retrieved_ids に含まれれば True。"""
    if not expected_chunks:
        return True  # 期待 chunk が未定義なら常に hit
    return any(
        _matches_expected_evidence(retrieved_id, expected_chunk)
        for retrieved_id in retrieved_ids
        for expected_chunk in expected_chunks
    )


def retrieval_precision_at_k(retrieved_ids: list[str], expected_chunks: list[str]) -> float:
    """Precision@k: top-k の中に expected chunk が何割含まれるか。"""
    if not expected_chunks:
        return 1.0
    hits = sum(
        1
        for expected_chunk in expected_chunks
        if any(
            _matches_expected_evidence(retrieved_id, expected_chunk)
            for retrieved_id in retrieved_ids
        )
    )
    return hits / len(expected_chunks)
