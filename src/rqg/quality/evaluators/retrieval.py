"""期待根拠が検索結果 top-k に含まれる割合を評価する。"""

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
    """期待根拠のいずれかが検索結果に含まれる場合に True を返す。"""
    if not expected_chunks:
        return True
    return any(
        _matches_expected_evidence(retrieved_id, expected_chunk)
        for retrieved_id in retrieved_ids
        for expected_chunk in expected_chunks
    )


def expected_evidence_recall_at_k(retrieved_ids: list[str], expected_chunks: list[str]) -> float:
    """検索結果 top-k に含まれた期待根拠の割合を返す。"""
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


def retrieval_precision_at_k(retrieved_ids: list[str], expected_chunks: list[str]) -> float:
    """後方互換のために残す expected_evidence_recall_at_k の別名。"""
    return expected_evidence_recall_at_k(retrieved_ids, expected_chunks)
