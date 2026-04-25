from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from rqg.domain import GateDecision
from rqg.quality.reporting import (
    GATE_REPORT_BUNDLE_ARTIFACT_TYPE,
    GATE_REPORT_BUNDLE_SCHEMA_VERSION,
    GATE_REPORT_BUNDLE_TYPE,
    GateReportArtifacts,
    build_gate_report_bundle_payload,
)


def test_build_gate_report_bundle_payload_includes_stable_contract_metadata() -> None:
    created_at = datetime(2026, 4, 20, 12, 30, tzinfo=timezone.utc)
    decision = GateDecision(
        run_id="run-contract",
        status="warn",
        reasons=["S1 pass rate below threshold"],
        metrics={"overall_pass_rate": 95.0, "s1_pass_rate": 90.0},
        next_actions=[],
        created_at=created_at,
    )
    artifacts = GateReportArtifacts(
        markdown="## Gate WARN",
        decision=decision,
        history_summary={"entries": 1},
        report_path=Path("runs/quality/gate-report.md"),
        decision_path=Path("runs/quality/gate-decision.json"),
        history_summary_path=Path("runs/quality/gate-history-summary.json"),
        history_path=Path("runs/quality/gate-decisions.jsonl"),
        bundle_path=Path("runs/quality/gate-report.json"),
    )

    payload = build_gate_report_bundle_payload(artifacts)

    assert payload["schema_version"] == GATE_REPORT_BUNDLE_SCHEMA_VERSION
    assert payload["artifact_type"] == GATE_REPORT_BUNDLE_ARTIFACT_TYPE
    assert payload["bundle_type"] == GATE_REPORT_BUNDLE_TYPE
    assert payload["generated_at"] == "2026-04-20T12:30:00Z"
    contract = payload["contract"]
    assert isinstance(contract, dict)
    assert contract["name"] == "rqg.gate_report_bundle"
    assert contract["version"] == GATE_REPORT_BUNDLE_SCHEMA_VERSION
    assert contract["stable_fields"] == [
        "schema_version",
        "artifact_type",
        "bundle_type",
        "contract",
        "generated_at",
        "run",
        "decision",
        "history_summary",
        "report_markdown",
        "artifact_paths",
    ]
    assert contract["required_fields"] == contract["stable_fields"]
    assert contract["optional_fields"] == []
    assert contract["required_run_fields"] == ["run_id", "status", "created_at"]
    assert contract["optional_run_fields"] == []
    assert contract["required_artifact_path_fields"] == [
        "report_path",
        "decision_path",
        "history_summary_path",
        "history_path",
        "bundle_path",
    ]
    assert contract["optional_artifact_path_fields"] == []
    assert "minor changes are additive" in contract["compatibility"]
    assert "empty strings" in contract["empty_value_rule"]
    run = payload["run"]
    assert isinstance(run, dict)
    assert payload["run"] == {
        "run_id": "run-contract",
        "status": "warn",
        "created_at": "2026-04-20T12:30:00Z",
    }
    decision_payload = payload["decision"]
    assert isinstance(decision_payload, dict)
    assert decision_payload["run_id"] == "run-contract"
    assert payload["history_summary"] == {"entries": 1}
    assert payload["report_markdown"] == "## Gate WARN"
    artifact_paths = payload["artifact_paths"]
    assert isinstance(artifact_paths, dict)
    assert list(artifact_paths) == contract["required_artifact_path_fields"]
    assert artifact_paths["bundle_path"] == Path("runs/quality/gate-report.json").as_posix()
