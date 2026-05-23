"""Plan draft case candidates from registry-selected Case Intents."""

from __future__ import annotations

from typing import Sequence

from rqg.case_assets import CaseIntentRegistry
from rqg.case_draft.draft_case import DraftCaseCandidate, SourceSection
from rqg.case_draft.engine import CaseDraftEngine
from rqg.case_draft.source_matcher import SourceSectionMatcher


class CaseDraftPlanner:
    """Connect Case Intent candidate selection to draft candidate generation.

    This internal planner does not connect to the existing gen_cases CLI, call an
    LLM, run retrieval, activate cases, or make release decisions.
    """

    def __init__(
        self,
        registry: CaseIntentRegistry,
        engine: CaseDraftEngine | None = None,
        source_matcher: SourceSectionMatcher | None = None,
    ) -> None:
        self._registry = registry
        self._engine = engine or CaseDraftEngine()
        self._source_matcher = source_matcher or SourceSectionMatcher()

    def create_drafts_for_affected_categories(
        self,
        categories: Sequence[str],
        source_section: SourceSection | None = None,
    ) -> list[DraftCaseCandidate]:
        """Create needs_review drafts for intents matching affected categories."""
        if not categories:
            return []
        intents = self._registry.find_candidates_for_affected_categories(categories)
        return [
            self._engine.create_draft_from_intent(
                intent,
                source_section=source_section,
            )
            for intent in intents
        ]

    def create_drafts_for_affected_categories_with_sections(
        self,
        categories: Sequence[str],
        sections: Sequence[SourceSection],
    ) -> list[DraftCaseCandidate]:
        """Create drafts using matched source sections per candidate intent."""
        if not categories:
            return []
        intents = self._registry.find_candidates_for_affected_categories(categories)
        return [
            self._engine.create_draft_from_intent(
                intent,
                source_section=self._source_matcher.select_for_intent(intent, sections),
            )
            for intent in intents
        ]


def create_drafts_for_affected_categories(
    registry: CaseIntentRegistry,
    categories: Sequence[str],
    source_section: SourceSection | None = None,
) -> list[DraftCaseCandidate]:
    """Convenience wrapper for category-based draft planning."""
    return CaseDraftPlanner(registry).create_drafts_for_affected_categories(
        categories,
        source_section=source_section,
    )
