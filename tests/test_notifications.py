from __future__ import annotations

import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from rqg.cli import main
from rqg.domain import GateDecision, GateNextAction, GatePackMetadata
from rqg.quality.check import CheckResult, ThresholdResult
from rqg.quality.notifications import _build_payload


def test_check_sends_notifications_from_rqg_config() -> None:
    workspace = Path("tests/.tmp") / f"{uuid.uuid4()}-notify"
    workspace.mkdir(parents=True, exist_ok=True)
    log_dir = workspace / "logs"
    config_path = workspace / ".rqg.yml"
    decision_path = log_dir / "gate-decision.json"
    config_path.write_text(
        "\n".join(
            [
                "notifications:",
                "  - type: webhook",
                "    webhook_url: https://notify.example.test/hook",
                "    notify_on: [fail]",
                "thresholds:",
                "  s1_pass_rate: 100.0",
                "  overall_pass_rate: 80.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_result = CheckResult(
        run_id="run-notify",
        current_runs=2,
        baseline_runs=0,
        overall_rate=50.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-notify"):
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b"ok")) as mocked_urlopen:
                exit_code = main(["check", "--log-dir", str(log_dir), "--config", str(config_path)])

    assert exit_code == 1
    assert mocked_urlopen.called
    request = mocked_urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["event"] == "rqg.gate_decision"
    assert payload["status"] == "fail"
    assert payload["decision_path"] == "gate-decision.json"


def test_check_warns_when_notification_delivery_fails(capsys, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    workspace = Path("tests/.tmp") / f"{uuid.uuid4()}-notify-fail"
    workspace.mkdir(parents=True, exist_ok=True)
    log_dir = workspace / "logs"
    config_path = workspace / ".rqg.yml"
    config_path.write_text(
        "\n".join(
            [
                "notifications:",
                "  - type: slack",
                "    webhook_url: https://notify.example.test/slack",
                "    notify_on: [fail]",
                "thresholds:",
                "  s1_pass_rate: 100.0",
                "  overall_pass_rate: 80.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_result = CheckResult(
        run_id="run-notify-fail",
        current_runs=1,
        baseline_runs=0,
        overall_rate=0.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1")],
    )

    with patch("rqg.quality.check.run_check", return_value=fake_result):
        with patch("rqg.quality.check.render_gate_markdown", return_value="md-notify"):
            with patch(
                "urllib.request.urlopen",
                side_effect=OSError("network down"),
            ):
                exit_code = main(["check", "--log-dir", str(log_dir), "--config", str(config_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Notification delivery failed" in captured.out


def test_notifications_do_not_include_sensitive_text() -> None:
    decision = GateDecision(
        run_id="run-safe-notify",
        status="fail",
        policy_status="block",
        reasons=[
            "answer=customer secret answer expected_answer=golden answer "
            "retrieved_evidence=chunk text endpoint=https://rag.example.com/search "
            "SECRET_TOKEN_ABC /internal/customer/path.md"
        ],
        metrics={"overall_pass_rate": 50.0, "s1_fail_count": 2.0},
        next_actions=[
            GateNextAction(
                failure_category="retrieval_miss",
                count=2,
                action="Review endpoint https://rag.example.com/search with SECRET_TOKEN_ABC",
                owner="/internal/customer/path.md",
                affected_case_ids=["QA-1"],
            )
        ],
        fallback_summary={"detail": "chunk_text SECRET_TOKEN_ABC"},
        needs_human_review=True,
        judge_reliability="medium",
        pack=GatePackMetadata(pack_name="hr-pack"),
        created_at=datetime.now(timezone.utc),
    )

    slack_payload = _build_payload(
        kind="slack",
        decision=decision,
        report_path="/tmp/customer/gate-report.md",
        decision_path="/tmp/customer/gate-decision.json",
    )
    webhook_payload = _build_payload(
        kind="webhook",
        decision=decision,
        report_path="/tmp/customer/gate-report.md",
        decision_path="/tmp/customer/gate-decision.json",
    )

    slack_text = json.dumps(slack_payload, ensure_ascii=False)
    webhook_text = json.dumps(webhook_payload, ensure_ascii=False)

    for text in (slack_text, webhook_text):
        assert "customer secret answer" not in text
        assert "golden answer" not in text
        assert "retrieved_evidence" not in text
        assert "chunk text" not in text
        assert "https://rag.example.com/search" not in text
        assert "SECRET_TOKEN_ABC" not in text
        assert "/internal/customer/path.md" not in text

    assert "retrieval_fail" in slack_text
    assert '"policy_status": "block"' in webhook_text
    assert '"report_path": "gate-report.md"' in webhook_text


def test_ci_notification_payloads_are_safe_summary_only() -> None:
    decision = GateDecision(
        run_id="run-ci-notify",
        status="fail",
        policy_status="block",
        reasons=["question=secret question answer=secret answer endpoint=https://rag.example.test"],
        reason_codes=["retrieval_miss"],
        metrics={"overall_pass_rate": 10.0, "s1_fail_count": 1.0},
        next_actions=[
            GateNextAction(
                failure_category="retrieval_miss",
                count=1,
                action="Review tenant ACME endpoint https://rag.example.test",
                owner="customer-owner@example.test",
                affected_case_ids=["ACME-CASE-1"],
            )
        ],
        fallback_summary={"chunk_text": "secret evidence"},
        needs_human_review=True,
        pack=GatePackMetadata(pack_name="tenant-secret-pack"),
        created_at=datetime.now(timezone.utc),
    )

    slack_payload = _build_payload(
        kind="slack",
        decision=decision,
        report_path="/home/runner/work/customer/gate-report-ci.md",
        decision_path="/home/runner/work/customer/gate-decision.json",
        report_mode="ci",
    )
    webhook_payload = _build_payload(
        kind="webhook",
        decision=decision,
        report_path="/home/runner/work/customer/gate-report-ci.md",
        decision_path="/home/runner/work/customer/gate-decision.json",
        report_mode="ci",
    )

    combined = json.dumps([slack_payload, webhook_payload], ensure_ascii=False)

    for forbidden in [
        "secret question",
        "secret answer",
        "secret evidence",
        "https://rag.example.test",
        "ACME",
        "customer-owner@example.test",
        "tenant-secret-pack",
        "/home/runner/work/customer",
    ]:
        assert forbidden not in combined

    assert "retrieval_fail" in combined
    assert '"policy_status": "block"' in combined
    assert "gate-report-ci.md" in combined


def test_notification_payload_uses_safe_projection_even_in_full_mode() -> None:
    raw_case_id = "ACME-CASE-777"
    decision = GateDecision(
        run_id="run-notify-full",
        status="fail",
        policy_status="block",
        reasons=[
            "raw fail_reason: question=How does ACME reset payroll? "
            "answer=Use source_doc payroll.md endpoint=https://rag.example.test"
        ],
        reason_codes=["retrieval_miss"],
        metrics={
            "overall_pass_rate": 25.0,
            "s1_pass_rate": 0.0,
            "s1_fail_count": 1.0,
            "current_runs": 4.0,
        },
        next_actions=[
            GateNextAction(
                failure_category="retrieval_miss",
                count=1,
                action="Investigate raw answer and expected_answer in source_doc",
                owner="customer-owner@example.test",
                affected_case_ids=[raw_case_id],
            )
        ],
        fallback_summary={"expected_evidence": "payroll.md#secret"},
        needs_human_review=True,
        execution_mode="external_real",
        created_at=datetime.now(timezone.utc),
    )

    payload = _build_payload(
        kind="webhook",
        decision=decision,
        report_path="C:/workspace/customer/logs/gate-report.md",
        decision_path="C:/workspace/customer/logs/gate-decision.json",
        report_mode="full",
    )
    serialized = json.dumps(payload, ensure_ascii=False)

    for forbidden in [
        "How does ACME reset payroll?",
        "Use source_doc",
        "expected_answer",
        "expected_evidence",
        "payroll.md",
        "source_doc",
        raw_case_id,
        "raw fail_reason",
        "https://rag.example.test",
        "customer-owner@example.test",
        "C:/workspace/customer/logs",
    ]:
        assert forbidden not in serialized

    assert "case_id_hash" in payload
    assert payload["case_id_hash"]
    assert payload["reason_codes"] == ["retrieval_fail", "needs_human_review"]
    assert payload["failure_type_code"] == "retrieval_fail"
    assert payload["report_path"] == "gate-report.md"
    assert payload["decision_path"] == "gate-decision.json"
    assert payload["report_mode"] == "full"
    assert payload["execution_mode"] == "external_real"


def test_notification_payload_policy_default_denies_raw_fields() -> None:
    from rqg.quality.artifact_exposure_policy import ArtifactType, FieldExposure
    from rqg.quality.artifact_exposure_policy import resolve_artifact_exposure

    policy = resolve_artifact_exposure(ArtifactType.NOTIFICATION_PAYLOAD, "full")

    assert policy.exposure_for("case_id") == FieldExposure.HASHED_ONLY
    assert policy.exposure_for("question") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("answer") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("expected_answer") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("source_doc") == FieldExposure.FORBIDDEN
    assert policy.exposure_for("unknown_future_field") == FieldExposure.FORBIDDEN
