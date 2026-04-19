"""Review-friendly output rendering for generated cases."""

from __future__ import annotations

import csv
from pathlib import Path

from rqg.domain import EvalCase
from rqg.presentation.markdown import render_eval_case_review_markdown
from rqg.quality.case_schema import REVIEW_OUTPUT_FIELDS


def render_cases_markdown(cases: list[EvalCase]) -> str:
    return render_eval_case_review_markdown(cases)


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
                writer.writerow(
                    {
                        "title": case.case_id,
                        "question": case.question,
                        "eval_mode": "evidence_keyword",
                        "expected_answer": "",
                        "expected_evidence": ";".join(case.expected_evidence),
                        "expected_keywords": ";".join(case.expected_keywords),
                        "severity": case.risk_level,
                        "category": case.category,
                        "notes": case.notes or "",
                    }
                )
        return output_path

    raise ValueError("review output must use .md or .csv")
