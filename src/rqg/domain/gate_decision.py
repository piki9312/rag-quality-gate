"""Gate decision domain model."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GateDecision(BaseModel):
    """A gate decision emitted from an evaluation run."""

    run_id: str
    status: Literal["pass", "warn", "fail"]
    reasons: list[str] = Field(default_factory=list)
    metrics: dict[str, float]
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
