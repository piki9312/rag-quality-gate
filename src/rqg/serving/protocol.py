"""Retrieval I/O protocol — RAG store の最小契約を定義する。

RQG のコアは品質ゲートであり、retrieval 実装ではない。
このモジュールは retrieval 結果の型契約と、store が満たすべき
最小インターフェースを定義する。adapter 層はこの契約に基づいて
外部RAGレスポンスを正規化し、runner に生レスポンスを漏らさない。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Retrieval 結果の正規化された1件。

    必須フィールド:
        chunk_id: チャンクの一意識別子。evidence 追跡に使用。
        source:   人がレビューで読める文書単位名 (例: "policy.md")。
        text:     チャンクのテキスト本文。

    補助フィールド:
        score:    検索スコア。外部RAGごとに意味が異なるため、
                  統一的な閾値比較には使わないこと。参考値。
        metadata: 将来拡張用。adapter が追加情報を透過的に渡す際に利用。
    """

    chunk_id: str
    source: str
    text: str
    score: float | None = None
    metadata: dict[str, Any] | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """runner 内部で既存の dict ベースのコードと互換を保つための変換。"""
        d: dict[str, Any] = {
            "chunk_id": self.chunk_id,
            "source": self.source,
            "text": self.text,
        }
        if self.score is not None:
            d["score"] = self.score
        if self.metadata:
            d["metadata"] = self.metadata
        return d


@runtime_checkable
class RAGStoreProtocol(Protocol):
    """RAG store が満たすべき最小 retrieval インターフェース。

    RQG runner はこの protocol にのみ依存し、具体的な store 実装
    (FAISS / HTTP / mock) の詳細を知らない。
    """

    def search(self, query: str, top_k: int = 6) -> list[dict[str, Any]]:
        """単一クエリで top_k 件のチャンクを検索する。

        返り値の各 dict は少なくとも以下のキーを持つこと:
            - chunk_id (str)
            - source (str)
            - text (str)
            - score (float) — 任意
        """
        ...

    def search_multi(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        """広めの retrieval を行い top_k 件を返す。

        「複数クエリ」ではなく「より広い候補から上位を選ぶ retrieval」を意味する。
        元クエリに対してキーワード展開やクエリ変換を行い、多角的に検索した結果を
        マージ・重複排除して上位 top_k 件を返す。

        デフォルト実装では search(top_k=top_k) に委譲してよい。
        """
        ...
