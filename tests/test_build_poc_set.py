from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from rqg.quality.case_merge import load_csv_rows
from rqg.quality.loader import load_cases
from rqg.quality.poc_set import (
    POC_CASE_OUTPUT_FIELDS,
    build_poc_case_set,
    load_poc_candidates,
    write_case_set_summary,
    write_poc_cases_csv,
)


def _write_case_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(dict.fromkeys([*POC_CASE_OUTPUT_FIELDS, *rows[0].keys()]))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def _case_row(
    *,
    case_id: str,
    severity: str,
    risk_domain: str,
    source_doc: str,
    question: str,
    notes: str,
    expected_evidence: str | None = None,
    source_type: str | None = None,
) -> dict[str, str]:
    row_notes = notes
    if source_type:
        row_notes = f"{row_notes};source_type:{source_type}" if row_notes else f"source_type:{source_type}"
    return {
        "case_id": case_id,
        "name": case_id,
        "status": "active",
        "severity": severity,
        "eval_mode": "evidence_keyword",
        "question": question,
        "expected_answer": "",
        "expected_evidence": expected_evidence or f"{source_doc}#sec-1",
        "expected_keywords": f"{risk_domain};policy",
        "category": risk_domain,
        "risk_domain": risk_domain,
        "required_action": "block" if severity == "S1" else "allow_with_warning",
        "evidence_required": "true" if expected_evidence is not None or source_doc else "false",
        "owner_role": "support_quality_owner",
        "source_doc": source_doc,
        "owner": "proofgate-demo",
        "min_case_score": "100" if severity == "S1" else "85",
        "updated_at": "2026-05-01",
        "last_reviewed_at": "2026-05-01",
        "notes": row_notes,
    }


def _generated_pool() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    domain_plan = [
        ("refund", 3, "S1"),
        ("cancellation", 2, "S1"),
        ("pricing", 6, "S2"),
        ("contract", 4, "S2"),
        ("deadline_procedure", 4, "S2"),
        ("deadline_procedure", 5, "S3"),
        ("general_faq", 1, "S2"),
    ]
    counter = 1
    for domain, count, band in domain_plan:
        for idx in range(count):
            rows.append(
                _case_row(
                    case_id=f"GEN-{counter:03d}",
                    severity="S1" if band == "S1" else "S2",
                    risk_domain=domain,
                    source_doc=f"{domain}.md",
                    question=(
                        f"{domain} generated S3 question {idx + 1}?"
                        if band == "S3"
                        else f"{domain} generated question {idx + 1}?"
                    ),
                    notes=f"poc_band:{band}",
                    source_type="generated",
                )
            )
            counter += 1
    return rows


def _template_pool() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    domain_plan = [
        ("refund", 4, "S1"),
        ("cancellation", 3, "S1"),
        ("pricing", 3, "S1"),
        ("contract", 2, "S1"),
        ("pricing", 2, "S2"),
        ("contract", 2, "S2"),
        ("deadline_procedure", 2, "S2"),
        ("refund", 1, "S2"),
        ("cancellation", 1, "S2"),
        ("general_faq", 1, "S2"),
    ]
    counter = 1
    for domain, count, band in domain_plan:
        for idx in range(count):
            rows.append(
                _case_row(
                    case_id=f"TPL-{counter:03d}",
                    severity="S1" if band == "S1" else "S2",
                    risk_domain=domain,
                    source_doc=f"{domain}.md",
                    question=f"{domain} template question {idx + 1}?",
                    notes=f"template_id:{domain}_{counter:03d};poc_band:{band};expected_decision:block",
                    source_type="template",
                )
            )
            counter += 1
    return rows


def _template_pool_without_s1() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in _template_pool():
        updated = dict(row)
        updated["severity"] = "S2"
        updated["required_action"] = "allow_with_warning"
        updated["min_case_score"] = "85"
        updated["notes"] = row["notes"].replace("poc_band:S1", "poc_band:S2")
        rows.append(updated)
    return rows


def test_template_cases_csv_can_be_loaded() -> None:
    path = Path("packs/customer_support_pack/template_cases.csv")
    candidates = load_poc_candidates(path, source_type="template")
    assert len(candidates) >= 30
    assert all(candidate.source_type == "template" for candidate in candidates)


def test_build_poc_set_generates_30_case_output_and_summary(tmp_path: Path) -> None:
    generated_path = _write_case_csv(tmp_path / "generated_cases.csv", _generated_pool())
    template_path = _write_case_csv(tmp_path / "template_cases.csv", _template_pool())

    result = build_poc_case_set(
        generated_path,
        template_path,
        total=30,
        s1=10,
        s2=15,
        s3=5,
        risk_profile="customer_support",
        strict=True,
    )

    assert len(result.selected_rows) == 30
    assert result.summary["severity_mix"] == {"S1": 10, "S2": 15, "S3": 5}
    assert result.summary["runtime_severity_mix"] == {"S1": 10, "S2": 20}


def test_s3_selection_band_rounds_runtime_severity_to_s2(tmp_path: Path) -> None:
    generated_rows = [
        _case_row(
            case_id="GEN-S3-001",
            severity="S2",
            risk_domain="deadline_procedure",
            source_doc="deadline.md",
            question="deadline generated S3?",
            notes="poc_band:S3",
            source_type="generated",
        )
    ]
    template_rows = [
        _case_row(
            case_id="TPL-S1-001",
            severity="S1",
            risk_domain="refund",
            source_doc="refund.md",
            question="refund template S1?",
            notes="template_id:refund_001;poc_band:S1",
            source_type="template",
        )
    ]

    generated_path = _write_case_csv(tmp_path / "generated.csv", generated_rows)
    template_path = _write_case_csv(tmp_path / "template.csv", template_rows)

    result = build_poc_case_set(
        generated_path,
        template_path,
        total=2,
        s1=1,
        s2=0,
        s3=1,
        risk_profile="customer_support",
        allow_fill=True,
    )

    row_by_id = {row["case_id"]: row for row in result.selected_rows}
    assert row_by_id["GEN-S3-001"]["severity"] == "S2"
    assert result.summary["severity_mix"] == {"S1": 1, "S2": 0, "S3": 1}
    assert result.summary["runtime_severity_mix"] == {"S1": 1, "S2": 1}


def test_strict_fails_when_s1_pool_is_short(tmp_path: Path) -> None:
    generated_path = _write_case_csv(tmp_path / "generated.csv", _generated_pool())
    template_path = _write_case_csv(tmp_path / "template.csv", _template_pool_without_s1())

    with pytest.raises(ValueError, match="requested 10 S1"):
        build_poc_case_set(
            generated_path,
            template_path,
            total=30,
            s1=10,
            s2=15,
            s3=5,
            risk_profile="customer_support",
            strict=True,
        )


def test_allow_fill_emits_warning_when_s1_pool_is_short(tmp_path: Path) -> None:
    generated_path = _write_case_csv(tmp_path / "generated.csv", _generated_pool())
    template_path = _write_case_csv(tmp_path / "template.csv", _template_pool_without_s1())

    result = build_poc_case_set(
        generated_path,
        template_path,
        total=30,
        s1=10,
        s2=15,
        s3=5,
        risk_profile="customer_support",
        allow_fill=True,
        warn_if_s1_missing=True,
    )

    assert len(result.selected_rows) == 30
    assert any("S1" in warning for warning in result.summary["warnings"])


def test_expected_evidence_empty_s1_template_is_not_selected(tmp_path: Path) -> None:
    generated_rows = _generated_pool()
    template_rows = _template_pool()
    template_rows.insert(
        0,
        _case_row(
            case_id="TPL-MISSING-EVIDENCE",
            severity="S1",
            risk_domain="refund",
            source_doc="refund.md",
            question="missing evidence refund?",
            notes="template_id:refund_missing;poc_band:S1",
            expected_evidence="",
            source_type="template",
        ),
    )
    generated_path = _write_case_csv(tmp_path / "generated.csv", generated_rows)
    template_path = _write_case_csv(tmp_path / "template.csv", template_rows)

    result = build_poc_case_set(
        generated_path,
        template_path,
        total=30,
        s1=10,
        s2=15,
        s3=5,
        risk_profile="customer_support",
        strict=True,
    )

    selected_ids = {row["case_id"] for row in result.selected_rows}
    assert "TPL-MISSING-EVIDENCE" not in selected_ids


def test_duplicate_questions_are_deduped_with_band_specific_preference(tmp_path: Path) -> None:
    generated_rows = [
        _case_row(
            case_id="GEN-S1-DUP",
            severity="S1",
            risk_domain="refund",
            source_doc="refund.md",
            question="duplicate refund question?",
            notes="poc_band:S1",
            source_type="generated",
        ),
        _case_row(
            case_id="GEN-S2-DUP",
            severity="S2",
            risk_domain="pricing",
            source_doc="pricing.md",
            question="duplicate pricing question?",
            notes="poc_band:S2",
            source_type="generated",
        ),
    ]
    template_rows = [
        _case_row(
            case_id="TPL-S1-DUP",
            severity="S1",
            risk_domain="refund",
            source_doc="refund.md",
            question="duplicate refund question?",
            notes="template_id:refund_dup;poc_band:S1",
            source_type="template",
        ),
        _case_row(
            case_id="TPL-S2-DUP",
            severity="S2",
            risk_domain="pricing",
            source_doc="pricing.md",
            question="duplicate pricing question?",
            notes="template_id:pricing_dup;poc_band:S2",
            source_type="template",
        ),
    ]
    generated_path = _write_case_csv(tmp_path / "generated.csv", generated_rows)
    template_path = _write_case_csv(tmp_path / "template.csv", template_rows)

    result = build_poc_case_set(
        generated_path,
        template_path,
        total=2,
        s1=1,
        s2=1,
        s3=0,
        risk_profile="customer_support",
        strict=True,
    )

    selected_ids = {row["case_id"] for row in result.selected_rows}
    assert "TPL-S1-DUP" in selected_ids
    assert "GEN-S1-DUP" not in selected_ids
    assert "GEN-S2-DUP" in selected_ids
    assert "TPL-S2-DUP" not in selected_ids


def test_same_input_produces_same_output(tmp_path: Path) -> None:
    generated_path = _write_case_csv(tmp_path / "generated.csv", _generated_pool())
    template_path = _write_case_csv(tmp_path / "template.csv", _template_pool())

    first = build_poc_case_set(
        generated_path,
        template_path,
        total=30,
        s1=10,
        s2=15,
        s3=5,
        risk_profile="customer_support",
        strict=True,
    )
    second = build_poc_case_set(
        generated_path,
        template_path,
        total=30,
        s1=10,
        s2=15,
        s3=5,
        risk_profile="customer_support",
        strict=True,
    )

    assert first.selected_rows == second.selected_rows
    assert first.summary == second.summary


def test_output_writer_preserves_additive_columns_and_loader_compatibility(tmp_path: Path) -> None:
    generated_path = _write_case_csv(tmp_path / "generated.csv", _generated_pool())
    template_path = _write_case_csv(tmp_path / "template.csv", _template_pool())
    result = build_poc_case_set(
        generated_path,
        template_path,
        total=30,
        s1=10,
        s2=15,
        s3=5,
        risk_profile="customer_support",
        strict=True,
    )

    output_path = write_poc_cases_csv(tmp_path / "cases.csv", result.selected_rows)
    summary_path = write_case_set_summary(tmp_path / "case_set_summary.json", result.summary)

    rows = load_csv_rows(output_path)
    assert "risk_domain" in rows[0]
    assert "required_action" in rows[0]
    assert "evidence_required" in rows[0]
    assert "owner_role" in rows[0]

    loaded_cases = load_cases(str(output_path))
    assert len(loaded_cases) == 30
    assert all(case.status == "active" for case in loaded_cases)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total"] == 30