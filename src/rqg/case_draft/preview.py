"""Review artifact generation for pattern-based draft case candidates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from rqg.case_assets import CaseIntentRegistry
from rqg.case_draft.csv_writer import write_draft_case_rows_csv
from rqg.case_draft.draft_case import SourceSection
from rqg.case_draft.pipeline import PatternDraftPipeline


@dataclass(frozen=True)
class DraftCasePreviewArtifact:
    """Metadata for a generated pattern draft review CSV artifact."""

    path: Path
    rows: list[dict[str, str]]
    row_count: int
    affected_categories: tuple[str, ...]


def write_pattern_draft_preview_csv(
    registry: CaseIntentRegistry,
    affected_categories: Sequence[str],
    sections: Sequence[SourceSection],
    output_path: Path,
) -> DraftCasePreviewArtifact:
    """Write pattern-based needs_review draft rows as a review CSV artifact."""
    categories = tuple(str(category) for category in affected_categories)
    rows = PatternDraftPipeline(registry).create_case_rows_for_affected_categories(
        categories,
        sections,
    )
    write_draft_case_rows_csv(rows, output_path)
    return DraftCasePreviewArtifact(
        path=output_path,
        rows=rows,
        row_count=len(rows),
        affected_categories=categories,
    )
