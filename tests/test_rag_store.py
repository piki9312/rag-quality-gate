"""Tests for RAGStore — ingest, search, persistence, reset."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest

from rqg.serving.rag import RAGStore, chunk_text

# FAISS cannot write to paths containing multibyte characters.
# Use a workspace-relative temp dir instead of pytest tmp_path.
_TEST_TMP = Path(__file__).resolve().parent / ".tmp"


@pytest.fixture()
def ascii_tmp():
    """Temp dir under tests/.tmp/ with ASCII-safe path."""
    d = _TEST_TMP / str(uuid.uuid4())
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def store(ascii_tmp, monkeypatch):
    """RAGStore with fallback embeddings (no SentenceTransformer download)."""

    class BrokenST:
        def __init__(self, *a, **kw):
            raise RuntimeError("offline")

    monkeypatch.setattr("rqg.serving.rag.SentenceTransformer", BrokenST)
    return RAGStore(index_dir=str(ascii_tmp / "idx"), auto_load=False)


# ------------------------------------------------------------------
# chunk_text
# ------------------------------------------------------------------


class TestChunkText:
    def test_empty_input(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        chunks = chunk_text("Hello world", chunk_size=900)
        assert len(chunks) == 1
        assert chunks[0] == "Hello world"

    def test_paragraph_splitting(self):
        # 900*2 chars across 3 paragraphs to force split
        text = "Paragraph one.\n\n" + "x" * 950 + "\n\n" + "y" * 950
        chunks = chunk_text(text, chunk_size=900, overlap=0)
        assert len(chunks) >= 2


# ------------------------------------------------------------------
# Ingest
# ------------------------------------------------------------------


class TestIngest:
    def test_add_text_returns_chunk_count(self, store):
        added = store.add_text("doc.md", "This is a test document for RAG.")
        assert added == 1
        assert len(store.metas) == 1
        assert store.metas[0]["source"] == "doc.md"

    def test_duplicate_doc_skipped(self, store):
        text = "Same document text for dedup test."
        first = store.add_text("doc.md", text)
        second = store.add_text("doc.md", text)
        assert first == 1
        assert second == 0
        assert len(store.metas) == 1

    def test_different_docs_both_added(self, store):
        store.add_text("a.md", "Document A content.")
        store.add_text("b.md", "Document B content.")
        assert len(store.metas) == 2

    def test_empty_text_returns_zero(self, store):
        added = store.add_text("empty.md", "")
        assert added == 0


# ------------------------------------------------------------------
# Search
# ------------------------------------------------------------------


class TestSearch:
    def test_search_returns_results(self, store):
        store.add_text("policy.md", "有給休暇は5営業日前までに申請してください。")
        results = store.search("有給休暇の申請", top_k=3)
        assert len(results) >= 1
        assert results[0]["source"] == "policy.md"
        assert "score" in results[0]

    def test_search_empty_store(self, store):
        results = store.search("anything", top_k=5)
        assert results == []

    def test_search_multi_returns_results(self, store):
        store.add_text("leave.md", "有給休暇の申請には上長承認が必要です。")
        results = store.search_multi("有給休暇の申請", top_k=5)
        assert len(results) >= 1

    def test_top_k_limits_results(self, store):
        for i in range(5):
            store.add_text(f"doc{i}.md", f"Document {i} about policy number {i}.")
        results = store.search("policy", top_k=2)
        assert len(results) <= 2


# ------------------------------------------------------------------
# Persistence
# ------------------------------------------------------------------


class TestPersistence:
    def test_save_and_reload(self, ascii_tmp, monkeypatch):
        class BrokenST:
            def __init__(self, *a, **kw):
                raise RuntimeError("offline")

        monkeypatch.setattr("rqg.serving.rag.SentenceTransformer", BrokenST)

        idx_dir = str(ascii_tmp / "persist")
        store1 = RAGStore(index_dir=idx_dir, auto_load=False)
        store1.add_text("doc.md", "Test persistence content.")
        assert len(store1.metas) == 1

        # Reload into new instance
        store2 = RAGStore(index_dir=idx_dir, auto_load=True)
        assert len(store2.metas) == 1
        assert store2.metas[0]["source"] == "doc.md"

        # Search should work after reload
        results = store2.search("persistence", top_k=3)
        assert len(results) >= 1

    def test_meta_json_structure(self, store, ascii_tmp):
        store.add_text("meta.md", "Metadata test content.")
        meta_path = ascii_tmp / "idx" / "meta.json"
        assert meta_path.exists()

        data = json.loads(meta_path.read_text(encoding="utf-8"))
        assert "metas" in data
        assert "next_id" in data
        assert "doc_ids" in data
        assert "emb_model" in data


# ------------------------------------------------------------------
# Reset
# ------------------------------------------------------------------


class TestReset:
    def test_reset_clears_state(self, store):
        store.add_text("doc.md", "Content to be reset.")
        assert len(store.metas) > 0

        store.reset()
        assert store.index is None
        assert store.metas == []
        assert store.doc_ids == set()
        assert store.next_id == 0

    def test_reset_deletes_files(self, store, ascii_tmp):
        store.add_text("doc.md", "Content to be reset.")
        idx_dir = ascii_tmp / "idx"
        assert (idx_dir / "faiss.index").exists()
        assert (idx_dir / "meta.json").exists()

        store.reset()
        assert not (idx_dir / "faiss.index").exists()
        assert not (idx_dir / "meta.json").exists()
