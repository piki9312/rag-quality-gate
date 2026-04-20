"""rqg scaffold sub-commands — init-snapshot, create-sample-case, create-sample-gate."""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone

from ..domain import DocumentSnapshot, EvalCase, GateDecision
from .helpers import write_json_output


def cmd_init_snapshot(args: argparse.Namespace) -> int:
    content_hash = hashlib.sha256(args.content.encode("utf-8")).hexdigest()
    snapshot = DocumentSnapshot(
        snapshot_id=args.snapshot_id,
        doc_id=args.doc_id,
        title=args.title,
        source_path=args.source_path,
        content_hash=content_hash,
        created_at=datetime.now(timezone.utc),
        version=args.version,
        metadata={},
    )
    output_path = write_json_output(args.output, snapshot)
    print(f"Saved snapshot JSON to {output_path}")
    return 0


def cmd_create_sample_case(args: argparse.Namespace) -> int:
    case = EvalCase(
        case_id="sample-case-001",
        question="What policy applies to paid leave requests?",
        expected_evidence=["Paid leave requests must be submitted in advance."],
        expected_keywords=["paid leave", "advance"],
        risk_level="S2",
        doc_snapshot_id="sample-snapshot-001",
        notes="Sample case for Phase 1 scaffolding.",
    )
    output_path = write_json_output(args.output, case)
    print(f"Saved eval case JSON to {output_path}")
    return 0


def cmd_create_sample_gate(args: argparse.Namespace) -> int:
    gate = GateDecision(
        run_id="sample-run-001",
        status="warn",
        reasons=["Sample gate decision for Phase 1 scaffolding."],
        metrics={"pass_rate": 0.8, "s1_pass_rate": 1.0},
        created_at=datetime.now(timezone.utc),
    )
    output_path = write_json_output(args.output, gate)
    print(f"Saved gate decision JSON to {output_path}")
    return 0
