"""Gate decision domain model."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GateNextAction(BaseModel):
    """Structured next action linked to a failure category."""

    failure_category: str = Field(min_length=1)
    count: int = Field(ge=1)
    action: str = Field(min_length=1)
    owner: str = "T.B.D."
    due: str = "T.B.D."

    model_config = ConfigDict(extra="forbid")


class GateDecision(BaseModel):
    """A gate decision emitted from an evaluation run."""

    run_id: str
    status: Literal["pass", "warn", "fail"]
    reasons: list[str] = Field(default_factory=list)
    metrics: dict[str, float]
    next_actions: list[GateNextAction] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
