"""Internal draft case candidate models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSection:
    """Small source section reference for draft generation."""

    section_id: str
    text: str
    source_ref: str | None = None


@dataclass(frozen=True)
class DraftCaseCandidate:
    """Vendor-reviewed draft case candidate generated from a Case Intent."""

    case_id: str
    status: str
    severity: str
    category: str
    question: str
    expected_answer: str
    expected_evidence: str
    notes: str
