"""Deterministic source section matching for draft generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from rqg.case_assets import CaseIntent
from rqg.case_draft.draft_case import SourceSection


@dataclass(frozen=True)
class _ScoredSection:
    score: int
    index: int
    section: SourceSection


class SourceSectionMatcher:
    """Select a source section for a Case Intent using simple exact substrings.

    This is not a retrieval implementation. It is a deterministic placeholder
    that can later be replaced by BM25, embeddings, or another retrieval layer.
    """

    def select_for_intent(
        self,
        intent: CaseIntent,
        sections: Sequence[SourceSection],
    ) -> SourceSection | None:
        """Return the highest-scoring source section for an intent."""
        if not sections:
            return None
        scored = [
            _ScoredSection(
                score=_score_section(intent.evidence_requirement, section),
                index=index,
                section=section,
            )
            for index, section in enumerate(sections)
        ]
        matches = [item for item in scored if item.score > 0]
        if not matches:
            return None
        # Stable tie-breaker: preserve caller-provided section order.
        best = sorted(matches, key=lambda item: (-item.score, item.index))[0]
        return best.section


def select_source_section_for_intent(
    intent: CaseIntent,
    sections: Sequence[SourceSection],
) -> SourceSection | None:
    """Convenience wrapper for deterministic source section matching."""
    return SourceSectionMatcher().select_for_intent(intent, sections)


def _score_section(requirements: Sequence[str], section: SourceSection) -> int:
    section_id = section.section_id.lower()
    source_ref = (section.source_ref or "").lower()
    text = section.text.lower()
    score = 0
    for requirement in requirements:
        needle = requirement.lower().strip()
        if not needle:
            continue
        if needle in section_id:
            score += 3
        if needle in source_ref:
            score += 2
        if needle in text:
            score += 1
    return score
