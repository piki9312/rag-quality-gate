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
    affected_case_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class GatePackMetadata(BaseModel):
    """Pack metadata carried alongside gate decisions for reuse and UI."""

    name: str = ""
    version: str = ""
    review_steward: str = ""
    pack_name: str = ""
    tenant_name: str = ""
    use_case: str = ""
    vertical: str = ""
    risk_profile: str = ""
    owner: str = ""
    environment: str = ""
    pack_version: str = ""
    source_pack: str = ""
    created_from_template: bool = False

    model_config = ConfigDict(extra="allow")


class GateDecision(BaseModel):
    """A gate decision emitted from an evaluation run."""

    run_id: str
    status: Literal["pass", "warn", "fail"]
    reasons: list[str] = Field(default_factory=list)
    metrics: dict[str, float]
    next_actions: list[GateNextAction] = Field(default_factory=list)
    judge_fallback_used: bool = False
    judge_fallback_count: int = Field(default=0, ge=0)
    judge_failure_types: dict[str, int] = Field(default_factory=dict)
    judge_reliability: Literal["high", "medium", "low"] = "high"
    embedding_fallback_used: bool = False
    embedding_fallback_count: int = Field(default=0, ge=0)
    embedding_fallback_reason: str | None = None
    needs_human_review: bool = False
    pack: GatePackMetadata | None = None
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
