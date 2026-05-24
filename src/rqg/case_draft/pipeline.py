"""Internal pattern-based draft row pipeline."""

from __future__ import annotations

from typing import Sequence

from rqg.case_assets import CaseIntentRegistry
from rqg.case_draft.draft_case import SourceSection
from rqg.case_draft.planner import CaseDraftPlanner
from rqg.case_draft.row_adapter import draft_candidates_to_case_rows


class PatternDraftPipeline:
    """Create cases.csv-compatible draft rows from pattern assets.

    This internal pipeline does not connect to the existing gen_cases CLI, call
    an LLM, perform retrieval, activate cases, or make release decisions.
    """

    def __init__(
        self,
        registry: CaseIntentRegistry,
        planner: CaseDraftPlanner | None = None,
    ) -> None:
        self._registry = registry
        self._planner = planner or CaseDraftPlanner(registry)

    def create_case_rows_for_affected_categories(
        self,
        categories: Sequence[str],
        sections: Sequence[SourceSection] = (),
    ) -> list[dict[str, str]]:
        """Create formal cases.csv-compatible needs_review draft rows."""
        if not categories:
            return []
        drafts = self._planner.create_drafts_for_affected_categories_with_sections(
            categories,
            sections,
        )
        return draft_candidates_to_case_rows(drafts)


def create_pattern_draft_case_rows(
    registry: CaseIntentRegistry,
    categories: Sequence[str],
    sections: Sequence[SourceSection] = (),
) -> list[dict[str, str]]:
    """Convenience wrapper for the internal pattern draft pipeline."""
    return PatternDraftPipeline(registry).create_case_rows_for_affected_categories(
        categories,
        sections,
    )
