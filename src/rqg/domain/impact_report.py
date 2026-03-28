"""Impact analysis report domain model."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImpactDetail(BaseModel):
    """A single impacted-case detail row."""

    case_id: str = Field(..., min_length=1)
    matched_evidence_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    match_mode: Literal["strict"] = "strict"

    model_config = ConfigDict(extra="forbid")


class ImpactReport(BaseModel):
    """Report describing which eval cases are impacted by snapshot changes."""

    old_snapshot_id: str = Field(..., min_length=1)
    new_snapshot_id: str = Field(..., min_length=1)
    changed_evidence_ids: list[str] = Field(default_factory=list)
    impacted_case_ids: list[str] = Field(default_factory=list)
    details: list[ImpactDetail] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
