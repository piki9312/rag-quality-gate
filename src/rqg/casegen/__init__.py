"""Case candidate generation for EvalCase scaffolding."""

from .generator import GeneratedCaseBundle, generate_eval_cases_from_snapshot
from .review import render_cases_markdown, write_review_output
from .sections import DocumentSection, extract_sections_from_snapshot

__all__ = [
    "DocumentSection",
    "GeneratedCaseBundle",
    "extract_sections_from_snapshot",
    "generate_eval_cases_from_snapshot",
    "render_cases_markdown",
    "write_review_output",
]
