"""Connection validation domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConnectionValidationResult(BaseModel):
    """Result of validating an external RAG connection."""

    endpoint: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(..., ge=1)
    ok: bool
    error_type: Literal[
        "none",
        "timeout_error",
        "auth_error",
        "server_error",
        "schema_error",
        "request_error",
    ] = "none"
    latency_ms: float = Field(..., ge=0)
    chunk_count: int = Field(default=0, ge=0)
    sample_chunk_ids: list[str] = Field(default_factory=list)
    sample_sources: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    checked_at: datetime

    model_config = ConfigDict(extra="forbid")
