from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("faiss")

from fastapi.testclient import TestClient


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_local_http_rag_search_returns_external_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("rqg.serving.rag.SentenceTransformer", None)

    docs_dir = tmp_path / "documents"
    index_dir = tmp_path / "index"
    _write(
        docs_dir / "policy.md",
        "Annual leave policy\n\nEmployees can request paid leave in advance.",
    )

    from rqg.serving.local_http_rag import create_local_http_rag_app

    app = create_local_http_rag_app(index_dir=str(index_dir), docs_dir=str(docs_dir))
    client = TestClient(app)

    response = client.post("/search", json={"query": "paid leave", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["chunk_count"] >= 1
    assert payload["results"]
    first = payload["results"][0]
    assert set(["chunk_id", "source", "text"]).issubset(first)


def test_local_http_rag_auth_requires_bearer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("rqg.serving.rag.SentenceTransformer", None)
    monkeypatch.setenv("RQG_LOCAL_RAG_KEY", "secret-token")

    from rqg.serving.local_http_rag import create_local_http_rag_app

    app = create_local_http_rag_app(
        index_dir=str(tmp_path / "index"),
        api_key_env="RQG_LOCAL_RAG_KEY",
    )
    client = TestClient(app)

    missing = client.post("/search", json={"query": "x", "top_k": 1})
    assert missing.status_code == 401

    wrong = client.post(
        "/search",
        json={"query": "x", "top_k": 1},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert wrong.status_code == 401

    ok = client.post(
        "/search",
        json={"query": "x", "top_k": 1},
        headers={"Authorization": "Bearer secret-token"},
    )
    assert ok.status_code == 200


def test_local_http_rag_notification_capture(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("rqg.serving.rag.SentenceTransformer", None)

    from rqg.serving.local_http_rag import create_local_http_rag_app

    app = create_local_http_rag_app(index_dir=str(tmp_path / "index"))
    client = TestClient(app)

    posted = client.post("/notify", json={"text": "RQG gate FAIL"})
    assert posted.status_code == 200
    assert posted.json()["event_count"] == 1

    events = client.get("/notify/events")
    assert events.status_code == 200
    payload = events.json()
    assert payload["count"] == 1
    assert payload["events"][0]["payload"]["text"] == "RQG gate FAIL"


def test_local_http_rag_rebuilds_index_when_embedding_model_changes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    docs_dir = tmp_path / "documents"
    index_dir = tmp_path / "index"
    _write(
        docs_dir / "policy.md",
        "Annual leave policy\n\nEmployees can request paid leave in advance.",
    )

    from rqg.serving.rag import RAGStore

    original_store = RAGStore(index_dir=str(index_dir), auto_load=False)
    original_store.emb_model_name = "test-model-v1"
    monkeypatch.setattr(
        original_store,
        "_embed",
        lambda texts: np.ones((len(texts), 3), dtype=np.float32),
    )
    original_store.add_text(
        source="policy.md", text=(docs_dir / "policy.md").read_text(encoding="utf-8")
    )

    monkeypatch.setattr("rqg.serving.rag.SentenceTransformer", None)

    from rqg.serving.local_http_rag import create_local_http_rag_app

    app = create_local_http_rag_app(index_dir=str(index_dir), docs_dir=str(docs_dir))
    client = TestClient(app)

    response = client.post("/search", json={"query": "paid leave", "top_k": 3})
    assert response.status_code == 200
    payload = response.json()
    assert payload["chunk_count"] >= 1
    assert app.state.ingested_files == 1
