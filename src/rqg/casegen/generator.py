"""EvalCase candidate generation pipeline."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from rqg.casegen.questions import (
    filter_reviewable_questions,
    generate_llm_questions,
    generate_rule_questions,
    infer_case_category,
    is_english_text,
    naturalize_question,
    normalize_question_text,
    suggest_keywords,
)
from rqg.casegen.sections import DocumentSection, extract_sections_from_snapshot
from rqg.domain import DocumentSnapshot, EvalCase
from rqg.quality.case_schema import infer_question_types

logger = logging.getLogger(__name__)

_CONTENT_TOKEN_RE = re.compile(r"[\w\u3040-\u30ff\u3400-\u9fff]")
_QUESTION_PREFIX_RE = re.compile(r"^[0-9]+[.)]\s*")
_SUBJECT_SPLIT_RE = re.compile(r"\s*(?:と|および|及び|並びに|/|／|・|and)\s*", re.IGNORECASE)
_ENGLISH_RE = re.compile(r"[A-Za-z]")
_QUESTION_SUFFIXES = (
    "はいつまでに対応する必要がありますか",
    "はいつまでに申請する必要がありますか",
    "はどの手順で申請しますか",
    "はどの手順ですか",
    "はどうやって申請しますか",
    "はどうやって行いますか",
    "の申請方法は何ですか",
    "の条件は何ですか",
    "の例外条件は何ですか",
    "の問い合わせ先はどこですか",
    "の要点は何ですか",
    "はいつまでですか",
    "はいくらですか",
    "はどこですか",
    "は何ですか",
    "when should ",
    "how should ",
)


@dataclass
class GeneratedCaseBundle:
    snapshot: DocumentSnapshot
    sections: list[DocumentSection]
    cases: list[EvalCase]


def _make_case_id(snapshot: DocumentSnapshot, section: DocumentSection, ordinal: int) -> str:
    prefix = (
        snapshot.title.strip()
        or Path(snapshot.source_path).stem
        or Path(snapshot.doc_id).stem
        or "doc"
    )
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
        category=infer_case_category(question, section),
        notes=notes,
    )


def _annotate_question_note(question: str, note: str) -> str:
    question_types = infer_question_types(question)
    if len(set(question_types)) < 2:
        return note
    return f"{note}; mixed_question:{','.join(question_types)}; manual_review_priority:high"


def _strip_question_subject(question: str) -> str:
    normalized = normalize_question_text(question)
    lowered = normalized.lower()

    english_prefixes = ("when should ", "how should ", "what are ", "what is ", "who should ")
    for prefix in english_prefixes:
        if lowered.startswith(prefix):
            body = normalized[len(prefix) :].strip()
            if body.endswith(" be handled"):
                return body[: -len(" be handled")].strip()
            if body.endswith(" be submitted"):
                return body[: -len(" be submitted")].strip()
            if body.endswith(" be reviewed"):
                return body[: -len(" be reviewed")].strip()
            return body

    for suffix in _QUESTION_SUFFIXES:
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)].strip()

    if normalized.endswith("ですか"):
        return normalized[: -len("ですか")].rstrip("は").strip()

    return normalized


def _split_subject_fragments(subject: str) -> list[str]:
    cleaned = _QUESTION_PREFIX_RE.sub("", subject.strip())
    fragments = [
        fragment.strip() for fragment in _SUBJECT_SPLIT_RE.split(cleaned) if fragment.strip()
    ]
    if len(fragments) > 1:
        return fragments

    if "の" in cleaned:
        fragments = [fragment.strip() for fragment in cleaned.split("の") if fragment.strip()]
        if len(fragments) > 1:
            return fragments

    return [cleaned] if cleaned else []


def _render_split_question(fragment: str, question_type: str, *, english: bool) -> str:
    subject = fragment.strip()
    if not subject:
        return ""

    if english:
        if question_type == "deadline":
            return f"When should {subject} be handled?"
        if question_type == "amount":
            return f"How much is {subject}?"
        if question_type == "procedure":
            return f"How should {subject} be submitted?"
        if question_type == "contact":
            return f"Who should be contacted for {subject}?"
        if question_type == "exception":
            return f"What are the exception conditions for {subject}?"
        if question_type == "list":
            return f"What are the key points of {subject}?"
        if question_type == "policy":
            return f"What are the requirements for {subject}?"
        return ""

    if question_type == "deadline":
        return f"{subject}はいつまでに対応する必要がありますか？"
    if question_type == "amount":
        return f"{subject}はいくらですか？"
    if question_type == "procedure":
        if subject.endswith(("方法", "手順", "提出方法", "申請方法")):
            return f"{subject}は何ですか？"
        return f"{subject}の申請方法は何ですか？"
    if question_type == "contact":
        if subject.endswith(("問い合わせ先", "窓口", "連絡先", "エスカレーション先")):
            return f"{subject}はどこですか？"
        return f"{subject}の問い合わせ先はどこですか？"
    if question_type == "exception":
        if subject.endswith("例外条件"):
            return f"{subject}は何ですか？"
        return f"{subject}の例外条件は何ですか？"
    if question_type == "list":
        if subject.endswith(("要点", "注意事項", "事由", "ポイント")):
            return f"{subject}は何ですか？"
        return f"{subject}の要点は何ですか？"
    if question_type == "policy":
        if subject.endswith(("条件", "ルール", "要件", "必要な証憑", "必要書類")):
            return f"{subject}は何ですか？"
        return f"{subject}の条件は何ですか？"
    return ""


def _split_candidate_questions(question: str) -> list[str]:
    question_types = infer_question_types(question)
    if len(set(question_types)) < 2:
        return []

    subject = _strip_question_subject(question)
    fragments = _split_subject_fragments(subject)
    english = bool(_ENGLISH_RE.search(question)) and not bool(
        re.search(r"[ぁ-んァ-ヶ一-龠々]", question)
    )

    candidates: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        fragment_types = infer_question_types(fragment)
        labels = fragment_types or question_types
        for label in labels:
            candidate = _render_split_question(fragment, label, english=english)
            normalized = normalize_question_text(candidate).lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            candidates.append(candidate)

    if candidates:
        return filter_reviewable_questions(candidates)
    return []


def _build_split_candidate_note(original_question: str, note: str) -> str:
    return (
        f"{note}; split_candidate_from:{normalize_question_text(original_question)}; "
        "manual_review_priority:medium"
    )


def _rule_question_limit(section: DocumentSection) -> int:
    return 3 if is_english_text(f"{section.heading}\n{section.content}") else 1


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

        for question in generate_rule_questions(
            section, max_questions=_rule_question_limit(section)
        ):
            question = naturalize_question(question, section)
            questions.append(
                (
                    question,
                    _annotate_question_note(
                        question,
                        f"auto-generated from {section.section_id}",
                    ),
                )
            )
            for split_question in _split_candidate_questions(question):
                split_question = naturalize_question(split_question, section)
                questions.append(
                    (
                        split_question,
                        _build_split_candidate_note(
                            question,
                            f"auto-generated split candidate from {section.section_id}",
                        ),
                    )
                )

        if mode == "hybrid" or use_llm:
            if use_llm:
                try:
                    llm_questions = generate_llm_questions(section, max_questions=2)
                except (ValueError, TypeError, RuntimeError, OSError) as exc:
                    logger.warning(
                        "llm question generation crashed for %s: %s", section.section_id, exc
                    )
                    llm_questions = []
            else:
                llm_questions = []
            for question in llm_questions:
                question = naturalize_question(question, section)
                questions.append(
                    (
                        question,
                        _annotate_question_note(
                            question,
                            f"auto-generated from {section.section_id} via llm",
                        ),
                    )
                )
                for split_question in _split_candidate_questions(question):
                    split_question = naturalize_question(split_question, section)
                    questions.append(
                        (
                            split_question,
                            _build_split_candidate_note(
                                question,
                                f"auto-generated split candidate from {section.section_id} via llm",
                            ),
                        )
                    )

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
