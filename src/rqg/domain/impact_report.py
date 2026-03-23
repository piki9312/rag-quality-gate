"""Impact analysis report domain model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ImpactReport(BaseModel):
    """Report describing which eval cases are impacted by snapshot changes."""

    old_snapshot_id: str = Field(..., min_length=1)
    new_snapshot_id: str = Field(..., min_length=1)
    changed_evidence_ids: list[str] = Field(default_factory=list)
    impacted_case_ids: list[str] = Field(default_factory=list)
    details: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
