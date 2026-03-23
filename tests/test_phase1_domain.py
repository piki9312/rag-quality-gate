from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from rqg.domain import DocumentSnapshot, EvalCase, GateDecision


def test_document_snapshot_valid() -> None:
    snapshot = DocumentSnapshot(
        snapshot_id="snapshot-001",
        doc_id="doc-001",
        title="Policy",
        source_path="docs/policy.md",
        content_hash="abc123",
        created_at=datetime.now(timezone.utc),
        version="v1",
        metadata={"team": "hr"},
    )

    assert snapshot.snapshot_id == "snapshot-001"
    assert '"snapshot_id":"snapshot-001"' in snapshot.model_dump_json()


def test_document_snapshot_rejects_empty_snapshot_id() -> None:
    with pytest.raises(ValidationError):
        DocumentSnapshot(
            snapshot_id="",
            doc_id="doc-001",
            title="Policy",
            source_path="docs/policy.md",
            content_hash="abc123",
            created_at=datetime.now(timezone.utc),
        )


def test_eval_case_valid() -> None:
    case = EvalCase(
        case_id="case-001",
        question="What is the reimbursement limit?",
        expected_evidence=["The reimbursement limit is 10,000 JPY."],
        expected_keywords=["reimbursement", "10,000"],
        risk_level="S1",
        doc_snapshot_id="snapshot-001",
    )

    assert case.risk_level == "S1"
    assert '"case_id":"case-001"' in case.model_dump_json()


def test_eval_case_rejects_empty_expected_evidence() -> None:
    with pytest.raises(ValidationError):
        EvalCase(
            case_id="case-001",
            question="What is the reimbursement limit?",
            expected_evidence=[],
            risk_level="S1",
            doc_snapshot_id="snapshot-001",
        )


def test_eval_case_rejects_invalid_risk_level() -> None:
    with pytest.raises(ValidationError):
        EvalCase(
            case_id="case-001",
            question="What is the reimbursement limit?",
            expected_evidence=["The reimbursement limit is 10,000 JPY."],
            risk_level="S3",
            doc_snapshot_id="snapshot-001",
        )


def test_gate_decision_valid() -> None:
    decision = GateDecision(
        run_id="run-001",
        status="pass",
        reasons=["All checks passed."],
        metrics={"pass_rate": 1.0},
        created_at=datetime.now(timezone.utc),
    )

    assert decision.status == "pass"
    assert '"run_id":"run-001"' in decision.model_dump_json()


def test_gate_decision_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        GateDecision(
            run_id="run-001",
            status="blocked",
            reasons=[],
            metrics={"pass_rate": 1.0},
            created_at=datetime.now(timezone.utc),
        )
