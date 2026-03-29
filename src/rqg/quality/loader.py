"""CSV ケースローダー — Quality Pack のテストケースを読み込む。"""

from __future__ import annotations

import csv
from pathlib import Path

from rqg.domain import EvalCase

from .models import QATestCase


def _split_semicolon_list(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(";") if item.strip()]


def eval_case_to_qa_test_case(
    eval_case: EvalCase,
    *,
    name: str | None = None,
    category: str = "general",
    owner: str = "",
    min_pass_rate: float = 0.0,
    last_reviewed_at: str = "",
) -> QATestCase:
    """Adapt an EvalCase into the legacy runner input model."""
    return QATestCase(
        case_id=eval_case.case_id,
        name=name or eval_case.case_id,
        question=eval_case.question,
        severity=eval_case.risk_level,
        expected_keywords=list(eval_case.expected_keywords),
        expected_chunks=list(eval_case.expected_evidence),
        golden_answer="",
        category=category,
        owner=owner,
        min_pass_rate=min_pass_rate,
        last_reviewed_at=last_reviewed_at,
    )


def qa_test_case_to_eval_case(
    case: QATestCase,
    *,
    doc_snapshot_id: str,
    notes: str | None = None,
) -> EvalCase:
    """Adapt a legacy QATestCase into the EvalCase domain model."""
    return EvalCase(
        case_id=case.case_id,
        question=case.question,
        expected_evidence=list(case.expected_chunks),
        expected_keywords=list(case.expected_keywords),
        risk_level=case.severity if case.severity in {"S1", "S2"} else "S2",
        doc_snapshot_id=doc_snapshot_id,
        notes=notes,
    )


def load_eval_cases(
    file_path: str,
    *,
    default_doc_snapshot_id: str = "unlinked-snapshot",
) -> list[EvalCase]:
    """Load EvalCase models from the existing CSV case format."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Test case file not found: {file_path}")

    cases: list[EvalCase] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            expected_evidence = _split_semicolon_list(
                row.get("expected_evidence", "") or row.get("expected_chunks", "")
            )
            expected_keywords = _split_semicolon_list(row.get("expected_keywords", ""))
            risk_level = (row.get("risk_level") or row.get("severity") or "S2").strip().upper()
            doc_snapshot_id = (row.get("doc_snapshot_id") or default_doc_snapshot_id).strip()

            cases.append(
                EvalCase(
                    case_id=row.get("case_id", ""),
                    question=row.get("question", ""),
                    expected_evidence=expected_evidence,
                    expected_keywords=expected_keywords,
                    risk_level=risk_level,
                    doc_snapshot_id=doc_snapshot_id,
                    notes=row.get("notes") or None,
                )
            )
    return cases


def load_cases(file_path: str) -> list[QATestCase]:
    """CSV ファイルから QATestCase のリストを読み込む。

    CSV カラム（必須: case_id, name, question。他はオプション）:
        case_id, name, severity, question, expected_chunks,
        expected_keywords, golden_answer, category, owner, min_pass_rate,
        last_reviewed_at
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Test case file not found: {file_path}")

    cases: list[QATestCase] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # セミコロン区切りのリスト
            expected_kw = _split_semicolon_list(row.get("expected_keywords", ""))
            expected_ch = _split_semicolon_list(row.get("expected_chunks", ""))
            min_pr = 0.0
            if row.get("min_pass_rate"):
                try:
                    min_pr = float(row["min_pass_rate"])
                except ValueError:
                    pass

            case = QATestCase(
                case_id=row.get("case_id", ""),
                name=row.get("name", ""),
                question=row.get("question", ""),
                severity=row.get("severity", "S2").strip().upper(),
                expected_keywords=expected_kw,
                expected_chunks=expected_ch,
                golden_answer=row.get("golden_answer", ""),
                category=row.get("category", "general"),
                owner=row.get("owner", ""),
                min_pass_rate=min_pr,
                last_reviewed_at=row.get("last_reviewed_at", "").strip(),
            )
            cases.append(case)
    return cases
