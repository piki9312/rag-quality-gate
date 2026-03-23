"""Evaluation case domain model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvalCase(BaseModel):
    """A single evaluation case definition."""

    case_id: str
    question: str = Field(..., min_length=1)
    expected_evidence: list[str] = Field(..., min_length=1)
    expected_keywords: list[str] = Field(default_factory=list)
    risk_level: Literal["S1", "S2"]
    doc_snapshot_id: str
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")
