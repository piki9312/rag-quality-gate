"""RAG パイプライン — チャンク分割・embedding・FAISS 検索。

rag_app から移植・再構成。パス設定は外部から注入可能。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DEFAULT_EMB_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
FALLBACK_EMB_DIM = 256


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    """段落境界を尊重したチャンク分割。"""
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []

    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""

    for p in paras:
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= chunk_size:
            buf = buf + "\n\n" + p
        else:
            chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)

    # overlap: 前チャンク末尾を次チャンク先頭に付与
    if overlap > 0 and len(chunks) >= 2:
        out = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = out[-1]
            prefix = prev[-overlap:]
            out.append((prefix + "\n" + chunks[i]).strip())
        chunks = out

    # 末尾が短すぎる場合は前に吸収
    if len(chunks) >= 2 and len(chunks[-1]) < chunk_size * 0.25:
        chunks[-2] = (chunks[-2] + "\n" + chunks[-1]).strip()
        chunks.pop()

    return [c for c in chunks if c]


class RAGStore:
    """FAISS ベースの RAG ストア。"""

    def __init__(
        self,
        index_dir: str = "index",
        emb_model: str | None = None,
        auto_load: bool = True,
    ):
        self.index_dir = index_dir
        self.index_path = os.path.join(index_dir, "faiss.index")
        self.meta_path = os.path.join(index_dir, "meta.json")
        os.makedirs(index_dir, exist_ok=True)

        self.emb_model_name = emb_model or os.getenv("EMB_MODEL", DEFAULT_EMB_MODEL)
        self.model = self._load_embedding_model()
        self.index: Optional[faiss.Index] = None
        self.metas: list[dict[str, Any]] = []
        self.doc_ids: set[str] = set()
        self.next_id = 0

        if auto_load:
            self._load()

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------

    def _load_embedding_model(self):
        try:
            return SentenceTransformer(self.emb_model_name)
        except Exception as exc:
            logger.warning(
                "failed to load embedding model '%s'; using local fallback embeddings: %s",
                self.emb_model_name,
                exc,
            )
            self.emb_model_name = "local-fallback-hash-embedding"
            return None

    def _fallback_embed(self, texts: list[str]) -> np.ndarray:
        vecs = np.zeros((len(texts), FALLBACK_EMB_DIM), dtype=np.float32)
        for row_idx, text in enumerate(texts):
            tokens = re.findall(r"\w+", text.lower())
            if not tokens:
                continue
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                bucket = int.from_bytes(digest[:4], "big") % FALLBACK_EMB_DIM
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vecs[row_idx, bucket] += sign

            norm = np.linalg.norm(vecs[row_idx])
            if norm > 0:
                vecs[row_idx] /= norm
        return vecs

    def _embed(self, texts: list[str]) -> np.ndarray:
        if self.model is None:
            return self._fallback_embed(texts)

        vecs = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype(np.float32)
        return vecs

    def _init_index(self, dim: int) -> None:
        self.index = faiss.IndexFlatIP(dim)

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def add_text(
        self, source: str, text: str, chunk_size: int = 900, overlap: int = 150
    ) -> int:
        """テキストを chunk 化して index に追加。重複ドキュメントはスキップ。"""
        doc_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        if doc_hash in self.doc_ids:
            logger.debug("duplicate doc skipped: %s", doc_hash)
            return 0

        chunks = chunk_text(text, chunk_size, overlap)
        if not chunks:
            return 0

        vecs = self._embed(chunks)
        if self.index is None:
            self._init_index(vecs.shape[1])
        self.index.add(vecs)  # type: ignore[union-attr]
        self.doc_ids.add(doc_hash)

        for i, ch in enumerate(chunks):
            chunk_id = f"{source}@{doc_hash}#chunk{i}"
            self.metas.append(
                {
                    "doc_id": doc_hash,
                    "chunk_id": chunk_id,
                    "chunk_index": i,
                    "source": source,
                    "text": ch,
                }
            )
            self.next_id += 1

        self.save()
        return len(chunks)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 6) -> list[dict[str, Any]]:
        if self.index is None or not self.metas:
            return []
        qvec = self._embed([query])
        k = min(top_k, len(self.metas))
        scores, idxs = self.index.search(qvec, k)
        results: list[dict[str, Any]] = []
        for pos, sc in zip(idxs[0].tolist(), scores[0].tolist()):
            if pos < 0:
                continue
            meta = dict(self.metas[pos])
            meta["score"] = float(sc)
            results.append(meta)
        return results

    def _keywordize(self, q: str) -> str:
        q2 = re.sub(r"[^\wぁ-んァ-ヶ一-龥]+", " ", q)
        toks = [t for t in q2.split() if len(t) >= 2]
        return " ".join(toks[:12])

    def search_multi(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        """Multi-Query Retrieval: 元質問 + キーワード版で検索しマージ。"""
        queries = [query, self._keywordize(query)]
        pool: list[dict[str, Any]] = []
        for q in queries:
            pool.extend(self.search(q, top_k=min(10, len(self.metas) or 10)))
        best: dict[str, dict[str, Any]] = {}
        for r in pool:
            cid = r["chunk_id"]
            if cid not in best or r.get("score", -1e9) > best[cid].get("score", -1e9):
                best[cid] = r
        merged = sorted(best.values(), key=lambda x: x.get("score", 0.0), reverse=True)
        return merged[:top_k]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        os.makedirs(self.index_dir, exist_ok=True)
        if self.index is not None:
            faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "metas": self.metas,
                    "next_id": self.next_id,
                    "emb_model": self.emb_model_name,
                    "doc_ids": sorted(self.doc_ids),
                },
                f,
                ensure_ascii=False,
            )

    def _load(self) -> None:
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                self.metas = d.get("metas", [])
                self.next_id = d.get("next_id", len(self.metas))
                self.doc_ids = set(d.get("doc_ids", []))
                if self.index is not None and self.index.ntotal != len(self.metas):
                    logger.warning(
                        "index/meta count mismatch (%d vs %d) — resetting",
                        self.index.ntotal,
                        len(self.metas),
                    )
                    self.index = None
                    self.metas = []
                    self.next_id = 0
            except Exception:
                logger.exception("failed to load index — starting fresh")
                self.index = None
                self.metas = []
                self.next_id = 0

    def reset(self) -> None:
        """メモリ状態を初期化し、永続ファイルを削除する。"""
        self.index = None
        self.metas = []
        self.doc_ids = set()
        self.next_id = 0
        for p in [self.index_path, self.meta_path]:
            if os.path.exists(p):
                os.remove(p)
