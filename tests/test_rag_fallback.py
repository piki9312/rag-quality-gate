from __future__ import annotations

import uuid

from rqg.serving.rag import RAGStore


def test_rag_store_falls_back_to_local_embeddings(monkeypatch):
    class BrokenSentenceTransformer:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("offline")

    monkeypatch.setattr("rqg.serving.rag.SentenceTransformer", BrokenSentenceTransformer)

    index_dir = f"tests/.tmp/{uuid.uuid4()}-fallback-index"
    store = RAGStore(index_dir=index_dir, auto_load=False)
    added = store.add_text(
        source="leave_policy.md",
        text="Paid leave requests must be submitted 5 business days in advance.",
    )
    results = store.search("paid leave request policy", top_k=3)

    assert store.emb_model_name == "local-fallback-hash-embedding"
    assert added == 1
    assert len(results) == 1
    assert results[0]["source"] == "leave_policy.md"
