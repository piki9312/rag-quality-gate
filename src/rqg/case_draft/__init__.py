"""Draft case generation primitives."""

from rqg.case_draft.csv_writer import (
    draft_case_rows_to_csv_text,
    validate_draft_case_row,
    validate_draft_case_rows,
    write_draft_case_rows_csv,
)
from rqg.case_draft.draft_case import DraftCaseCandidate, SourceSection
from rqg.case_draft.engine import CaseDraftEngine
from rqg.case_draft.pipeline import PatternDraftPipeline, create_pattern_draft_case_rows
from rqg.case_draft.planner import CaseDraftPlanner
from rqg.case_draft.preview import DraftCasePreviewArtifact, write_pattern_draft_preview_csv
from rqg.case_draft.row_adapter import (
    draft_candidate_to_case_row,
    draft_candidates_to_case_rows,
)
from rqg.case_draft.source_matcher import SourceSectionMatcher
from rqg.case_draft.validators import validate_draft_case_candidate

__all__ = [
    "CaseDraftEngine",
    "CaseDraftPlanner",
    "DraftCasePreviewArtifact",
    "DraftCaseCandidate",
    "PatternDraftPipeline",
    "SourceSectionMatcher",
    "SourceSection",
    "create_pattern_draft_case_rows",
    "draft_candidate_to_case_row",
    "draft_candidates_to_case_rows",
    "draft_case_rows_to_csv_text",
    "validate_draft_case_row",
    "validate_draft_case_rows",
    "validate_draft_case_candidate",
    "write_draft_case_rows_csv",
    "write_pattern_draft_preview_csv",
]
