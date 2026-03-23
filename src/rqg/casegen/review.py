"""Review-friendly output rendering for generated cases."""

from __future__ import annotations

import csv
from pathlib import Path

from rqg.domain import EvalCase


def render_cases_markdown(cases: list[EvalCase]) -> str:
    lines = ["# EvalCase Review", ""]
    lines.append("| case_id | question | expected_evidence | risk_level | notes |")
    lines.append("|---------|----------|-------------------|------------|-------|")
    for case in cases:
        evidence = ", ".join(case.expected_evidence)
        notes = case.notes or ""
        question = case.question.replace("\n", " ")
        lines.append(
            f"| {case.case_id} | {question} | {evidence} | {case.risk_level} | {notes} |"
        )
    return "\n".join(lines) + "\n"


def write_review_output(path: str | Path, cases: list[EvalCase]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()

    if suffix == ".md":
        output_path.write_text(render_cases_markdown(cases), encoding="utf-8")
        return output_path

    if suffix == ".csv":
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["case_id", "question", "expected_evidence", "expected_keywords", "risk_level", "doc_snapshot_id", "notes"],
            )
            writer.writeheader()
            for case in cases:
                writer.writerow(
                    {
                        "case_id": case.case_id,
                        "question": case.question,
                        "expected_evidence": ";".join(case.expected_evidence),
                        "expected_keywords": ";".join(case.expected_keywords),
                        "risk_level": case.risk_level,
                        "doc_snapshot_id": case.doc_snapshot_id,
                        "notes": case.notes or "",
                    }
                )
        return output_path

    raise ValueError("review output must use .md or .csv")
