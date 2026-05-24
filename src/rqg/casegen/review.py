"""Review-friendly output rendering for generated cases."""

from __future__ import annotations

import csv
from pathlib import Path

from rqg.domain import EvalCase
from rqg.presentation.markdown import render_eval_case_review_markdown
from rqg.quality.case_schema import REVIEW_OUTPUT_FIELDS, infer_source_doc

_UNAPPROVED_DRAFT_MARKER = "answer_status:unapproved-draft"


def _append_note_marker(notes: str | None, marker: str) -> str:
    parts = [part.strip() for part in (notes or "").split(";") if part.strip()]
    if marker not in parts:
        parts.append(marker)
    return "; ".join(parts)


def _review_notes(case: EvalCase) -> str:
    notes = case.notes or ""
    if case.expected_answer.strip():
        return _append_note_marker(notes, _UNAPPROVED_DRAFT_MARKER)
    return notes


def _cases_with_review_markers(cases: list[EvalCase]) -> list[EvalCase]:
    marked_cases: list[EvalCase] = []
    for case in cases:
        notes = _review_notes(case)
        if notes != (case.notes or ""):
            marked_cases.append(case.model_copy(update={"notes": notes}))
        else:
            marked_cases.append(case)
    return marked_cases


def render_cases_markdown(cases: list[EvalCase]) -> str:
    return render_eval_case_review_markdown(_cases_with_review_markers(cases))


def write_review_output(path: str | Path, cases: list[EvalCase]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()

    if suffix == ".md":
        output_path.write_text(render_cases_markdown(cases), encoding="utf-8")
        return output_path

    if suffix == ".csv":
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=REVIEW_OUTPUT_FIELDS)
            writer.writeheader()
            for case in cases:
                # source_doc is a reviewer aid only; expected_evidence remains authoritative.
                writer.writerow(
                    {
                        "title": case.case_id,
                        "question": case.question,
                        "eval_mode": "evidence_keyword",
                        "expected_answer": case.expected_answer,
                        "expected_evidence": ";".join(case.expected_evidence),
                        "expected_keywords": ";".join(case.expected_keywords),
                        "source_doc": infer_source_doc(
                            expected_evidence=case.expected_evidence,
                            doc_snapshot_id=case.doc_snapshot_id,
                        ),
                        "severity": case.risk_level,
                        "category": case.category,
                        "notes": _review_notes(case),
                    }
                )
        return output_path

    raise ValueError("review output must use .md or .csv")
