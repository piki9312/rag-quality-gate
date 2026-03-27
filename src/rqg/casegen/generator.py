"""EvalCase candidate generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import re

from rqg.casegen.questions import (
    normalize_question_text,
    generate_llm_questions,
    generate_rule_questions,
    suggest_keywords,
)
from rqg.casegen.sections import DocumentSection, extract_sections_from_snapshot
from rqg.domain import DocumentSnapshot, EvalCase

logger = logging.getLogger(__name__)

_CONTENT_TOKEN_RE = re.compile(r"[\w\u3040-\u30ff\u3400-\u9fff]")


@dataclass
class GeneratedCaseBundle:
    snapshot: DocumentSnapshot
    sections: list[DocumentSection]
    cases: list[EvalCase]


def _make_case_id(snapshot: DocumentSnapshot, section: DocumentSection, ordinal: int) -> str:
    prefix = snapshot.title.strip() or Path(snapshot.source_path).stem or Path(snapshot.doc_id).stem or "doc"
    slug = prefix.lower().replace(" ", "_").replace("-", "_")
    return f"{slug}_{ordinal:03d}"


def _build_eval_case(
    snapshot: DocumentSnapshot,
    section: DocumentSection,
    question: str,
    ordinal: int,
    notes: str,
) -> EvalCase:
    return EvalCase(
        case_id=_make_case_id(snapshot, section, ordinal),
        question=question,
        expected_evidence=[section.section_id],
        expected_keywords=suggest_keywords(section),
        risk_level="S2",
        doc_snapshot_id=snapshot.snapshot_id,
        notes=notes,
    )


def _is_caseworthy_section(section: DocumentSection) -> bool:
    compact = "".join(section.content.split())
    if len(compact) < 15:
        return False
    return bool(_CONTENT_TOKEN_RE.search(compact))


def generate_eval_cases_from_snapshot(
    snapshot: DocumentSnapshot,
    *,
    snapshot_path: str | Path | None = None,
    mode: str = "rule",
    max_cases: int = 50,
    use_llm: bool = False,
) -> GeneratedCaseBundle:
    """Generate EvalCase candidates from a document snapshot."""
    sections = extract_sections_from_snapshot(snapshot, snapshot_path=snapshot_path)
    cases: list[EvalCase] = []
    ordinal = 0

    for section in sections:
        if not _is_caseworthy_section(section):
            continue

        questions: list[tuple[str, str]] = []

        for question in generate_rule_questions(section, max_questions=1):
            questions.append((question, f"auto-generated from {section.section_id}"))

        if mode == "hybrid" or use_llm:
            if use_llm:
                try:
                    llm_questions = generate_llm_questions(section, max_questions=2)
                except Exception as exc:
                    logger.warning("llm question generation crashed for %s: %s", section.section_id, exc)
                    llm_questions = []
            else:
                llm_questions = []
            for question in llm_questions:
                questions.append((question, f"auto-generated from {section.section_id} via llm"))

        deduped_questions: list[tuple[str, str]] = []
        seen_questions: set[str] = set()
        for question, note in questions:
            question_key = normalize_question_text(question).lower()
            if question_key and question_key not in seen_questions:
                seen_questions.add(question_key)
                deduped_questions.append((question, note))

        for question, note in deduped_questions:
            ordinal += 1
            cases.append(_build_eval_case(snapshot, section, question, ordinal, note))
            if len(cases) >= max_cases:
                return GeneratedCaseBundle(snapshot=snapshot, sections=sections, cases=cases)

    return GeneratedCaseBundle(snapshot=snapshot, sections=sections, cases=cases)
