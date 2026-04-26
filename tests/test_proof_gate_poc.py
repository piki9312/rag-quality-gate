from __future__ import annotations

import json
from pathlib import Path

from rqg.quality.check import CheckResult, ThresholdResult, build_gate_decision
from rqg.quality.loader import load_cases
from rqg.quality.monthly_summary import build_monthly_summary_payload


def test_customer_support_pack_metadata_and_case_risk_fields_load() -> None:
    cases = load_cases("packs/customer_support_pack/cases.csv")
    first = cases[0]

    assert len(cases) >= 10
    assert first.case_id == "CS-S1-REFUND-001"
    assert first.risk_domain == "refund"
    assert first.required_action == "block"
    assert first.evidence_required is True


def test_policy_status_blocks_s1_fail_while_preserving_legacy_status() -> None:
    result = CheckResult(
        run_id="proofgate-run",
        current_runs=1,
        baseline_runs=0,
        overall_rate=0.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
        failure_categories={"retrieval_miss": 1},
        failure_case_ids={"retrieval_miss": ["CS-S1-REFUND-001"]},
    )

    decision = build_gate_decision(
        result,
        pack_metadata={
            "pack_id": "customer_support_pack",
            "pack_name": "Customer Support AI Quality Pack",
        },
    )

    assert decision.status == "fail"
    assert decision.policy_status == "block"
    assert "retrieval_fail" in decision.reason_codes
    assert decision.metrics["s1_fail_count"] == 1.0
    assert decision.pack is not None
    assert decision.pack.pack_id == "customer_support_pack"


def test_reliability_fallback_surfaces_in_decision_contract() -> None:
    result = CheckResult(
        run_id="proofgate-fallback",
        current_runs=1,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=1,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 100.0, True, "1/1")],
        judge_fallback_count=1,
        judge_failure_types={"parse_error": 1},
        judge_reliability="low",
        needs_human_review=True,
    )

    decision = build_gate_decision(result)

    assert decision.status == "pass"
    assert decision.policy_status == "needs_human_review"
    assert decision.judge_reliability == "low"
    assert decision.fallback_summary["judge_fallback_used"] is True
    assert "judge_fallback_used" in decision.reason_codes
    assert decision.approval.approval_required is True
    assert decision.approval.approval_status == "pending"


def test_monthly_summary_exposes_proof_gate_business_fields(tmp_path: Path) -> None:
    decision = build_gate_decision(
        CheckResult(
            run_id="proofgate-monthly",
            current_runs=1,
            baseline_runs=0,
            overall_rate=0.0,
            s1_rate=0.0,
            s1_passed=0,
            s1_total=1,
            thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
            embedding_fallback_count=1,
            embedding_fallback_used=True,
            embedding_fallback_reason="model_load_error",
            needs_human_review=True,
        ),
        pack_metadata={"pack_id": "customer_support_pack"},
    )
    payload = json.loads(decision.model_dump_json())
    payload["created_at"] = "2026-04-15T00:00:00Z"

    from rqg.domain import GateDecision

    summary = build_monthly_summary_payload(
        [GateDecision.model_validate(payload)],
        month="2026-04",
    )

    assert summary["month"] == "2026-04"
    assert summary["pack_id"] == "customer_support_pack"
    assert summary["blocked_runs"] == 1
    assert summary["s1_incidents_detected"] == 1
    assert summary["fallback_summary"]["embedding_fallback_count"] == 1
