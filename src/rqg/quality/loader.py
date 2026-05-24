"""CSV ケースローダー — Quality Pack のテストケースを読み込む。"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from pydantic import ValidationError

from rqg.domain import EvalCase

from .case_schema import infer_eval_mode, normalize_eval_mode
from .models import QATestCase


def _split_semicolon_list(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(";") if item.strip()]


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return _split_semicolon_list(value)
    return []


def normalize_case_status(value: object) -> str:
    if value is None:
        return "active"
    status = str(value).strip().lower()
    return status or "active"


def filter_cases_by_status(
    cases: list[QATestCase], *, allowed_statuses: set[str] | None = None
) -> list[QATestCase]:
    """Return only cases whose normalized status is in allowed_statuses."""
    if allowed_statuses is None:
        allowed = {"active"}
    else:
        allowed = {normalize_case_status(status) for status in allowed_statuses}
    return [case for case in cases if normalize_case_status(case.status) in allowed]


def eval_case_to_qa_test_case(
    eval_case: EvalCase,
    *,
    name: str | None = None,
    category: str | None = None,
    owner: str = "",
    min_case_score: float = 0.0,
    last_reviewed_at: str = "",
) -> QATestCase:
    """Adapt an EvalCase into the legacy runner input model."""
    return QATestCase(
        case_id=eval_case.case_id,
        name=name or eval_case.case_id,
        question=eval_case.question,
        severity=eval_case.risk_level,
        eval_mode="evidence_keyword",
        expected_keywords=list(eval_case.expected_keywords),
        expected_evidence=list(eval_case.expected_evidence),
        expected_answer="",
        status=eval_case.status,
        category=category or eval_case.category,
        owner=owner,
        min_case_score=min_case_score,
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
        expected_answer=case.expected_answer,
        expected_evidence=list(case.expected_evidence),
        expected_keywords=list(case.expected_keywords),
        risk_level=case.severity if case.severity in {"S1", "S2"} else "S2",
        status=normalize_case_status(case.status),
        doc_snapshot_id=doc_snapshot_id,
        category=case.category or "general",
        notes=notes or case.notes or None,
    )


def _load_cases_from_json(path: Path) -> list[QATestCase]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON case file: {path}") from exc

    if not isinstance(payload, list):
        raise ValueError(f"JSON case file must be a list: {path}")

    cases: list[QATestCase] = []
    for idx, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"JSON case entry at index {idx} must be an object")

        try:
            eval_case = EvalCase.model_validate(item)
        except ValidationError:
            case_id = str(item.get("case_id", "")).strip()
            question = str(item.get("question", "")).strip()
            if not case_id or not question:
                raise ValueError(f"Invalid JSON case entry at index {idx}")

            severity = str(item.get("severity") or item.get("risk_level") or "S2").strip().upper()
            expected_keywords = _as_list(item.get("expected_keywords"))
            expected_evidence = _as_list(
                item.get("expected_evidence")
                if "expected_evidence" in item
                else item.get("expected_chunks")
            )
            expected_answer = str(item.get("expected_answer") or item.get("golden_answer") or "")
            eval_mode = normalize_eval_mode(item.get("eval_mode"))
            if not eval_mode:
                eval_mode = infer_eval_mode(
                    expected_answer=expected_answer,
                    expected_evidence=expected_evidence,
                    expected_keywords=expected_keywords,
                )
            raw_min_case_score = item.get("min_case_score") or item.get("min_pass_rate") or 0.0
            try:
                min_case_score = float(raw_min_case_score) if raw_min_case_score else 0.0
            except (TypeError, ValueError):
                min_case_score = 0.0

            qa_case = QATestCase(
                case_id=case_id,
                name=str(item.get("name") or case_id),
                question=question,
                severity=severity,
                eval_mode=eval_mode,
                expected_keywords=expected_keywords,
                expected_evidence=expected_evidence,
                expected_answer=expected_answer,
                category=str(item.get("category", "general")),
                risk_domain=str(item.get("risk_domain") or item.get("category") or "general"),
                required_action=str(item.get("required_action") or ""),
                evidence_required=bool(item.get("evidence_required") or expected_evidence),
                owner_role=str(item.get("owner_role") or ""),
                owner=str(item.get("owner", "")),
                min_case_score=min_case_score,
                last_reviewed_at=str(item.get("last_reviewed_at", "")).strip(),
            )
            cases.append(qa_case)
            continue

        cases.append(eval_case_to_qa_test_case(eval_case))

    return cases


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
            doc_snapshot_id = (
                row.get("doc_snapshot_id") or row.get("source_doc") or default_doc_snapshot_id
            ).strip()

            cases.append(
                EvalCase(
                    case_id=row.get("case_id", ""),
                    question=row.get("question", ""),
                    expected_answer=(row.get("expected_answer") or row.get("golden_answer") or ""),
                    expected_evidence=expected_evidence,
                    expected_keywords=expected_keywords,
                    risk_level=risk_level,
                    status=normalize_case_status(row.get("status")),
                    doc_snapshot_id=doc_snapshot_id,
                    category=(row.get("category") or "general").strip() or "general",
                    notes=row.get("notes") or None,
                )
            )
    return cases


def load_cases(file_path: str) -> list[QATestCase]:
    """CSV/JSON ファイルから QATestCase のリストを読み込む。

    CSV カラム（必須: case_id, name, question。他はオプション）:
        case_id, name, status, severity, eval_mode, question,
        expected_evidence/expected_chunks, expected_keywords,
        expected_answer/golden_answer, category, source_doc, owner,
        min_case_score/min_pass_rate, updated_at, last_reviewed_at, notes
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Test case file not found: {file_path}")

    if path.suffix.lower() == ".json":
        return _load_cases_from_json(path)

    cases: list[QATestCase] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # セミコロン区切りのリスト (new + legacy field names)
            expected_kw = _split_semicolon_list(row.get("expected_keywords", ""))
            expected_ev = _split_semicolon_list(
                row.get("expected_evidence", "") or row.get("expected_chunks", "")
            )
            expected_answer = row.get("expected_answer", "") or row.get("golden_answer", "")
            eval_mode = normalize_eval_mode(row.get("eval_mode", ""))
            if not eval_mode:
                eval_mode = infer_eval_mode(
                    expected_answer=expected_answer,
                    expected_evidence=expected_ev,
                    expected_keywords=expected_kw,
                )
            min_cs = 0.0
            raw_score = row.get("min_case_score") or row.get("min_pass_rate") or ""
            if raw_score:
                try:
                    min_cs = float(raw_score)
                except ValueError:
                    pass

            case = QATestCase(
                case_id=row.get("case_id", ""),
                name=row.get("name", ""),
                question=row.get("question", ""),
                severity=row.get("severity", "S2").strip().upper(),
                status=row.get("status", "active").strip() or "active",
                eval_mode=eval_mode,
                expected_keywords=expected_kw,
                expected_evidence=expected_ev,
                expected_answer=expected_answer,
                category=row.get("category", "general"),
                risk_domain=row.get("risk_domain", "").strip() or row.get("category", "general"),
                required_action=(
                    row.get("required_action", "").strip()
                    or _infer_required_action(row.get("severity", "S2"))
                ),
                evidence_required=_as_bool(row.get("evidence_required", "")) or bool(expected_ev),
                owner_role=row.get("owner_role", "").strip(),
                source_doc=row.get("source_doc", ""),
                owner=row.get("owner", ""),
                min_case_score=min_cs,
                updated_at=row.get("updated_at", "").strip(),
                last_reviewed_at=row.get("last_reviewed_at", "").strip(),
                notes=row.get("notes", "").strip(),
            )
            cases.append(case)
    return cases


def _infer_required_action(severity: object) -> str:
    normalized = str(severity or "").strip().upper()
    if normalized == "S1":
        return "block"
    if normalized == "S2":
        return "allow_with_warning"
    return "allow"


def _as_bool(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "required"}
