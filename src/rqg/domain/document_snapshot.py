"""Document snapshot domain model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentSnapshot(BaseModel):
    """Snapshot metadata for an ingested document."""

    snapshot_id: str = Field(..., min_length=1)
    doc_id: str = Field(..., min_length=1)
    title: str
    source_path: str
    content_hash: str
    created_at: datetime
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
