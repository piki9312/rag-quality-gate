"""Local FastAPI wrapper that exposes the built-in RAG store via /search."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from .rag import RAGStore

logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=50)


def create_local_http_rag_app(
    *,
    index_dir: str,
    docs_dir: str | None = None,
    api_key_env: str | None = None,
) -> FastAPI:
    """Create a local FastAPI app that speaks the external /search contract."""
    Path(index_dir).mkdir(parents=True, exist_ok=True)
    store = RAGStore(index_dir=index_dir)
    ingested_files = 0
    ingested_chunks = 0

    if docs_dir and store.index is None:
        ingested_files, ingested_chunks = _ingest_docs_if_needed(store, docs_dir)

    app = FastAPI(title="RQG Local HTTP RAG", version="0.1.0")
    app.state.store = store
    app.state.index_dir = index_dir
    app.state.docs_dir = docs_dir
    app.state.ingested_files = ingested_files
    app.state.ingested_chunks = ingested_chunks
    app.state.notification_events = []

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "ok": True,
            "index_dir": index_dir,
            "docs_dir": docs_dir,
            "chunk_count": len(store.metas),
            "ingested_files": ingested_files,
            "ingested_chunks": ingested_chunks,
            "checked_at": _utcnow().isoformat(),
        }

    @app.post("/search")
    def search(
        payload: SearchRequest,
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _authorize_request(api_key_env=api_key_env, authorization=authorization)
        results = store.search(payload.query, top_k=payload.top_k)
        return {
            "results": results,
            "query": payload.query,
            "top_k": payload.top_k,
            "chunk_count": len(results),
        }

    @app.post("/notify")
    async def notify(request: Request) -> dict[str, Any]:
        body = await request.json()
        event = {
            "received_at": _utcnow().isoformat(),
            "headers": {
                "content-type": request.headers.get("content-type", ""),
            },
            "payload": body,
        }
        app.state.notification_events.append(event)
        return {"ok": True, "event_count": len(app.state.notification_events)}

    @app.get("/notify/events")
    def notify_events(clear: bool = False) -> dict[str, Any]:
        events = list(app.state.notification_events)
        if clear:
            app.state.notification_events.clear()
        return {"count": len(events), "events": events}

    return app


def _authorize_request(*, api_key_env: str | None, authorization: str | None) -> None:
    if not api_key_env:
        return

    expected = os.environ.get(api_key_env, "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API key environment variable is not set: {api_key_env}",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token",
        )

    provided = authorization.removeprefix("Bearer ").strip()
    if provided != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Bearer token",
        )


def _ingest_docs_if_needed(store: RAGStore, docs_dir: str) -> tuple[int, int]:
    doc_root = Path(docs_dir)
    if not doc_root.exists() or not doc_root.is_dir():
        raise ValueError(f"docs_dir not found or is not a directory: {doc_root}")

    ingested_files = 0
    ingested_chunks = 0
    for path in sorted(doc_root.rglob("*")):
        if path.suffix.lower() not in {".md", ".txt"} or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        added = store.add_text(source=path.name, text=text)
        if added > 0:
            ingested_files += 1
            ingested_chunks += added

    logger.info(
        "local HTTP RAG ingest completed: docs_dir=%s files=%d chunks=%d",
        doc_root,
        ingested_files,
        ingested_chunks,
    )
    return ingested_files, ingested_chunks


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)