"""rqg.serving — RAG serving layer (chunk / embed / search / generate)."""

from .protocol import RAGStoreProtocol, RetrievedChunk

__all__ = ["RAGStoreProtocol", "RetrievedChunk"]
