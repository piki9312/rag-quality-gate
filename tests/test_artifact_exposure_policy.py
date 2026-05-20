from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from rqg.quality.artifact_exposure_policy import (
    ArtifactType,
    FieldExposure,
    resolve_artifact_exposure,
)
from rqg.quality.check import (
    CheckResult,
    ThresholdResult,
    build_case_report_rows,
    build_ci_case_report_rows,
    build_gate_decision,
    render_customer_summary_markdown,
)
from rqg.quality.models import QARunRecord, QATestCase
from rqg.quality.reporting import GateReportArtifacts, build_gate_report_bundle_payload


def _result() -> CheckResult:
    return CheckResult(
        run_id="run-exposure",
        current_runs=1,
        baseline_runs=0,
        overall_rate=0.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
        current_records=[
            QARunRecord(
                timestamp=datetime.now(timezone.utc),
                run_id="run-exposure",
                case_id="CASE-CUSTOMER-SECRET",
                severity="S1",
                category="refund",
                risk_domain="billing",
                required_action="block",
                passed=False,
                failure_type="keyword_miss",
                failure_category="keyword_miss",
                reasons=["raw fail reason with customer contract detail"],
                answer="raw AI answer with customer detail",
                answer_hash="answer-hash-safe",
                retrieved_ids=["customer-doc#secret"],
            )
        ],
        active_cases=[
            QATestCase(
                case_id="CASE-CUSTOMER-SECRET",
                name="Customer case name",
                question="raw customer question?",
                severity="S1",
                expected_answer="raw expected answer",
                expected_evidence=["customer-doc#secret"],
                category="refund",
                risk_domain="billing",
                source_doc="customer/refund-policy.md",
            )
        ],
    )


def _artifacts(result: CheckResult, *, report_mode: str) -> GateReportArtifacts:
    return GateReportArtifacts(
        markdown="md",
        decision=build_gate_decision(result),
        history_summary={
            "entries": 1,
            "status_mix": {"pass": 0, "warn": 0, "fail": 1},
            "summary_lines": [],
        },
        report_path=Path("gate-report.md"),
        decision_path=Path("gate-decision.json"),
        history_summary_path=Path("gate-history-summary.json"),
        history_path=Path("gate-decisions.jsonl"),
        bundle_path=Path("gate-report.json"),
        check_result=result,
        report_mode=report_mode,
    )


def test_redacted_gate_report_and_customer_summary_use_safe_fields_only() -> None:
    result = _result()
    payload = build_gate_report_bundle_payload(_artifacts(result, report_mode="redacted"))
    customer_summary = render_customer_summary_markdown(result, report_mode="redacted")
    serialized = json.dumps(payload, ensure_ascii=False) + customer_summary
    case_row = payload["cases"][0]

    assert "raw customer question" not in serialized
    assert "raw expected answer" not in serialized
    assert "customer/refund-policy.md" not in serialized
    assert "raw AI answer with customer detail" not in serialized
    assert "customer-doc#secret" not in serialized
    assert "raw fail reason with customer contract detail" not in serialized

    assert case_row["severity"] == "S1"
    assert case_row["pass_fail"] == "fail"
    assert case_row["answer_hash"] == "answer-hash-safe"
    assert case_row["case_id_hash"]
    assert case_row["case_id"].startswith("case:")


def test_ci_case_rows_use_hash_and_safe_reason_code_only() -> None:
    case_row = build_ci_case_report_rows(_result())[0]
    serialized = json.dumps(case_row, ensure_ascii=False)

    assert "CASE-CUSTOMER-SECRET" not in serialized
    assert "raw customer question" not in serialized
    assert "customer/refund-policy.md" not in serialized
    assert "raw fail reason with customer contract detail" not in serialized

    assert case_row["case_id_hash"]
    assert case_row["failure_type_code"] == "keyword_miss"
    assert case_row["severity"] == "S1"
    assert case_row["pass_fail"] == "fail"


def test_full_case_rows_preserve_existing_sensitive_fields() -> None:
    case_row = build_case_report_rows(_result(), report_mode="full")[0]

    assert case_row["case_id"] == "CASE-CUSTOMER-SECRET"
    assert case_row["question"] == "raw customer question?"
    assert case_row["expected_answer"] == "raw expected answer"
    assert case_row["expected_evidence"] == ["customer-doc#secret"]
    assert case_row["retrieved_evidence"] == ["customer-doc#secret"]
    assert case_row["ai_answer"] == "raw AI answer with customer detail"
    assert case_row["source_doc"] == "customer/refund-policy.md"
    assert case_row["fail_reason"] == "raw fail reason with customer contract detail"


def test_history_summary_policy_hashes_ids_and_denies_raw_content() -> None:
    policy = resolve_artifact_exposure(ArtifactType.HISTORY_SUMMARY, "full")

    assert policy.exposure_for("overall_pass_rate") == FieldExposure.ALLOWED
    assert policy.exposure_for("prompt_hash") == FieldExposure.ALLOWED
    assert policy.exposure_for("case_id") == FieldExposure.HASHED_ONLY
    assert policy.exposure_for("target_docs") == FieldExposure.HASHED_ONLY
    assert policy.exposure_for("source_doc") == FieldExposure.HASHED_ONLY
    assert policy.exposure_for("question") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("answer") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("expected_answer") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("raw_fail_reason") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("unknown_future_field") == FieldExposure.FORBIDDEN


def test_safe_gate_decision_history_policy_hashes_ids_and_denies_raw_content() -> None:
    policy = resolve_artifact_exposure(ArtifactType.GATE_DECISION_HISTORY_SAFE, "full")

    assert policy.exposure_for("run_id") == FieldExposure.ALLOWED
    assert policy.exposure_for("model_name") == FieldExposure.ALLOWED
    assert policy.exposure_for("adapter_config_hash") == FieldExposure.ALLOWED
    assert policy.exposure_for("retrieval_config_hash") == FieldExposure.ALLOWED
    assert policy.exposure_for("case_id") == FieldExposure.HASHED_ONLY
    assert policy.exposure_for("target_docs") == FieldExposure.HASHED_ONLY
    assert policy.exposure_for("source_doc") == FieldExposure.HASHED_ONLY
    assert policy.exposure_for("question") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("answer") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("expected_answer") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("raw_fail_reason") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("review_steward") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("unknown_future_field") == FieldExposure.FORBIDDEN
