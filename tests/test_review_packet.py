from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from rqg.domain import ReleaseDecision, map_customer_severity
from rqg.quality.check import CheckResult, ThresholdResult, build_gate_decision
from rqg.quality.models import QARunRecord, QATestCase
from rqg.quality.reporting import (
    GateReportArtifacts,
    build_customer_review_markdown,
    build_gate_report_bundle_payload,
    build_review_packet_full,
    build_review_packet_safe,
)


def _review_packet_artifacts(*, report_mode: str = "full") -> GateReportArtifacts:
    record = QARunRecord(
        timestamp=datetime(2026, 5, 19, 0, 0, tzinfo=timezone.utc),
        run_id="run-review-packet",
        case_id="VIP_REFUND_CASE",
        severity="S1",
        category="refund_policy",
        risk_domain="refund_policy",
        required_action="block",
        passed=False,
        failure_type="source_mismatch",
        failure_category="evidence_mismatch",
        reasons=["VIP refund answer contradicted the approved refund policy"],
        answer="Raw answer: refund is always available for VIP customers.",
        retrieved_ids=["refund_policy.md#sec-1"],
        evidence_match=False,
        retrieval_hit=True,
        evidence_recall=0.25,
    )
    case = QATestCase(
        case_id="VIP_REFUND_CASE",
        name="VIP refund policy",
        question="Can a VIP customer get a refund after the deadline?",
        severity="S1",
        expected_answer="Refunds after the deadline are not allowed.",
        expected_evidence=["refund_policy.md#sec-1"],
        expected_keywords=["deadline", "not allowed"],
        category="refund_policy",
        risk_domain="refund_policy",
        required_action="block",
        source_doc=r"C:\customer\docs\VIP refund policy.md",
        owner="ACME policy owner",
        updated_at="2026-05-01",
        notes="pattern:FP-REFUND-001",
    )
    result = CheckResult(
        run_id="run-review-packet",
        current_runs=1,
        baseline_runs=0,
        overall_rate=0.0,
        s1_rate=0.0,
        s1_passed=0,
        s1_total=1,
        thresholds=[
            ThresholdResult("S1 pass rate", 100.0, 0.0, False, "0/1"),
        ],
        failure_categories={"evidence_mismatch": 1},
        failure_case_ids={"evidence_mismatch": ["VIP_REFUND_CASE"]},
        current_records=[record],
        active_cases=[case],
        run_provenance={
            "doc_snapshot_ids": ["snapshot-refund-v2"],
            "source_of_truth_type": "approved_policy",
            "source_of_truth": "ACME internal policy corpus",
            "stale_doc_policy": "reject_docs_older_than_30_days",
            "change_event": {
                "change_event_id": "change-refund-202605",
                "change_type": "document_update",
                "changed_assets": [r"C:\customer\docs\VIP refund policy.md"],
                "affected_documents": [r"C:\customer\docs\VIP refund policy.md"],
                "affected_business_categories": ["refund_policy"],
                "change_summary": "VIP refund policy changed",
                "target_release": "ACME May release",
            },
        },
    )
    decision = build_gate_decision(
        result,
        failure_actions={"evidence_mismatch": "Align answer with approved refund policy"},
        pack_metadata={"pack_name": "customer-support-ai", "change_event": "refund policy update"},
    )
    return GateReportArtifacts(
        markdown="# safe report\n",
        customer_summary_markdown="# customer summary\n",
        decision=decision,
        history_summary={"entries": 1, "status_mix": {"pass": 0, "warn": 0, "fail": 1}},
        report_path=Path("gate-report.md"),
        customer_summary_path=Path("customer-summary.md"),
        decision_path=Path("gate-decision.json"),
        history_summary_path=Path("gate-history-summary.json"),
        history_path=Path("gate-decisions.jsonl"),
        bundle_path=Path("gate-report.json"),
        check_result=result,
        report_mode=report_mode,
    )


def _ready_review_packet_artifacts(
    *,
    report_mode: str = "full",
    include_source_of_truth: bool = True,
    include_versions: bool = True,
    include_stale_policy: bool = True,
    include_change_event: bool = True,
    change_type: str = "document_update",
    include_changed_assets: bool = True,
    include_affected_documents: bool = True,
    affected_business_categories: list[str] | None = None,
    active_cases: list[QATestCase] | None = None,
    review_stage: str | None = None,
) -> GateReportArtifacts:
    record = QARunRecord(
        timestamp=datetime(2026, 5, 19, 0, 0, tzinfo=timezone.utc),
        run_id="run-ready-packet",
        case_id="REFUND_OK_CASE",
        severity="S2",
        category="refund_policy",
        risk_domain="refund_policy",
        required_action="review",
        passed=True,
        answer="Compliant answer.",
        retrieved_ids=["refund_policy.md#sec-2"],
        evidence_match=True,
        retrieval_hit=True,
    )
    case = QATestCase(
        case_id="REFUND_OK_CASE",
        name="Refund policy ok",
        question="Can a customer request a refund within the deadline?",
        severity="S2",
        expected_answer="Refunds are allowed within the deadline.",
        expected_evidence=["refund_policy.md#sec-2"],
        category="refund_policy",
        risk_domain="refund_policy",
        source_doc="refund_policy.md",
        updated_at="2026-05-01",
    )
    cases = active_cases if active_cases is not None else [case]
    provenance = {
        "source_of_truth_type": "approved_policy" if include_source_of_truth else "",
        "source_of_truth": "approved refund policy" if include_source_of_truth else "",
        "stale_doc_policy": "reject_docs_older_than_30_days" if include_stale_policy else "",
    }
    if review_stage is not None:
        provenance["review_stage"] = review_stage
    if include_versions:
        provenance["doc_snapshot_ids"] = ["snapshot-ready-v1"]
    if include_change_event:
        provenance["change_event"] = {
            "change_event_id": "change-ready-202605",
            "change_type": change_type,
            "changed_assets": ["refund_policy.md"] if include_changed_assets else [],
            "affected_documents": ["refund_policy.md"] if include_affected_documents else [],
            "affected_business_categories": affected_business_categories or ["refund_policy"],
            "change_summary": "Refund FAQ update",
            "target_release": "2026-05-release",
        }
    result = CheckResult(
        run_id="run-ready-packet",
        current_runs=1,
        baseline_runs=0,
        overall_rate=100.0,
        s1_rate=100.0,
        s1_passed=0,
        s1_total=0,
        thresholds=[
            ThresholdResult("Overall pass rate", 90.0, 100.0, True, "1/1"),
        ],
        failure_categories={},
        failure_case_ids={},
        current_records=[record],
        active_cases=cases,
        run_provenance=provenance,
    )
    decision = build_gate_decision(
        result,
        failure_actions={},
        pack_metadata={"pack_name": "customer-support-ai"},
    )
    return GateReportArtifacts(
        markdown="# report\n",
        customer_summary_markdown="# customer summary\n",
        decision=decision,
        history_summary={},
        report_path=Path("gate-report.md"),
        customer_summary_path=Path("customer-summary.md"),
        decision_path=Path("gate-decision.json"),
        history_summary_path=Path("gate-history-summary.json"),
        history_path=Path("gate-decisions.jsonl"),
        bundle_path=Path("gate-report.json"),
        check_result=result,
        report_mode=report_mode,
    )


def test_review_packet_has_required_sections() -> None:
    packet = build_review_packet_safe(_review_packet_artifacts(report_mode="ci"))

    assert packet.run_summary.run_id == "run-review-packet"
    assert packet.decision.customer_status == "No-Go"
    assert packet.decision_explanation.headline
    assert packet.decision_explanation.blocking_reasons
    assert packet.severity_summary.critical == 1
    assert packet.risk_breakdown.evidence_mismatch == 1
    assert packet.report_sections.executive_summary
    assert packet.report_sections.decision
    assert packet.report_sections.scope
    assert packet.report_sections.major_risks
    assert packet.production_readiness.status == "not_ready"
    assert packet.delivery_review.status == "not_deliverable"
    assert packet.delivery_review.unresolved_s1_count == 1
    assert packet.blocking_items
    assert packet.customer_shareability.status == "shareable"
    assert packet.customer_submission_readiness.status == "not_recommended"
    assert packet.review_stage == "post_delivery_change"
    assert packet.document_corpus.document_count == 1
    assert packet.document_corpus.has_document_versions is True
    assert packet.change_summary.change_type == "document_update"
    assert packet.evidence_policy.includes_full_evidence is False


def test_safe_review_packet_excludes_raw_question_answer_and_evidence() -> None:
    packet = build_review_packet_safe(_review_packet_artifacts(report_mode="ci"))
    payload = json.dumps(packet.model_dump(mode="json"), ensure_ascii=False)

    assert "Can a VIP customer" not in payload
    assert "Raw answer" not in payload
    assert "refund_policy.md#sec-1" not in payload
    assert "VIP_REFUND_CASE" not in payload
    assert "VIP refund policy" not in payload
    assert "ACME policy owner" not in payload
    assert "ACME May release" not in payload
    assert "C:\\customer\\docs" not in payload
    assert packet.customer_shareability.forbidden_fields_detected == []
    assert packet.major_failures[0].case_id == ""
    assert packet.major_failures[0].case_id_hash
    assert packet.major_failures[0].safe_reason_code == "evidence_mismatch"
    assert packet.document_corpus.target_documents == []
    assert packet.document_corpus.source_of_truth == ""
    assert packet.document_corpus.version_hashes
    assert packet.change_summary.changed_assets == []
    assert packet.change_summary.affected_documents == []
    assert packet.change_summary.change_id_hash


def test_full_review_packet_keeps_detail_references() -> None:
    packet = build_review_packet_full(_review_packet_artifacts(report_mode="full"))
    failure = packet.major_failures[0]

    assert packet.evidence_policy.includes_full_evidence is True
    assert failure.case_id == "VIP_REFUND_CASE"
    assert failure.question_summary.startswith("Can a VIP customer")
    assert "Raw answer" in failure.actual_summary
    assert failure.full_detail_ref == "case:VIP_REFUND_CASE"
    assert "snapshot-refund-v2" in packet.scope.document_versions
    assert packet.document_corpus.source_of_truth == "ACME internal policy corpus"
    assert packet.document_corpus.target_documents[0].title == "VIP refund policy.md"
    assert packet.document_corpus.target_documents[0].owner == "ACME policy owner"
    assert packet.document_corpus.target_documents[0].source_path == (
        r"C:\customer\docs\VIP refund policy.md"
    )
    assert packet.change_summary.changed_assets == [r"C:\customer\docs\VIP refund policy.md"]
    assert packet.change_summary.affected_documents == [r"C:\customer\docs\VIP refund policy.md"]
    assert packet.customer_shareability.status == "needs_review"
    assert "full_evidence_mode" in packet.customer_shareability.forbidden_fields_detected


def test_customer_severity_mapping_is_conservative() -> None:
    assert (
        map_customer_severity(
            internal_severity="S1",
            failure_category="policy_gap",
            business_category="refund_policy",
            required_action="block",
        )
        == "Critical"
    )
    assert (
        map_customer_severity(
            internal_severity="S1",
            failure_category="evidence_mismatch",
            business_category="general",
        )
        == "High"
    )
    assert (
        map_customer_severity(
            internal_severity="S2",
            failure_category="exception_omission",
            business_category="general",
        )
        == "Medium"
    )
    assert (
        map_customer_severity(
            internal_severity="S2",
            failure_category="minor_wording",
            business_category="general",
        )
        == "Low"
    )


def test_blocking_reasons_include_s1_and_evidence_mismatch() -> None:
    packet = build_review_packet_safe(_review_packet_artifacts(report_mode="ci"))
    codes = {reason.reason_code for reason in packet.decision_explanation.blocking_reasons}

    assert "s1_case_failed" in codes
    assert "evidence_mismatch" in codes
    assert any(reason.why_it_blocks for reason in packet.decision_explanation.blocking_reasons)


def test_gate_report_bundle_includes_review_packet_without_breaking_contract() -> None:
    payload = build_gate_report_bundle_payload(_review_packet_artifacts(report_mode="ci"))
    review_packet = payload["review_packet"]
    serialized = json.dumps(review_packet, ensure_ascii=False)

    assert payload["schema_version"] == "1.0"
    assert review_packet["packet_mode"] == "safe"
    assert review_packet["report_sections"]["executive_summary"]
    assert review_packet["report_sections"]["delivery_review"]
    assert payload["customer_review_markdown"].startswith("# 変更後品質確認レポート")
    assert "Raw answer" not in payload["customer_review_markdown"]
    assert "Can a VIP customer" not in payload["customer_review_markdown"]
    assert "C:\\customer\\docs" not in payload["customer_review_markdown"]
    assert "corpus=(" in review_packet["report_sections"]["scope"]
    assert "change_type=document_update" in review_packet["report_sections"]["change_summary"]
    assert "Raw answer" not in serialized
    assert "Can a VIP customer" not in serialized
    assert "refund_policy.md#sec-1" not in serialized
    assert "VIP refund policy" not in serialized
    assert "ACME policy owner" not in serialized
    assert "ACME May release" not in serialized


def test_gate_report_bundle_uses_safe_review_packet_even_in_full_mode() -> None:
    payload = build_gate_report_bundle_payload(_review_packet_artifacts(report_mode="full"))
    review_packet = payload["review_packet"]
    internal_packet = payload["internal_review_packet"]
    serialized = json.dumps(review_packet, ensure_ascii=False)

    assert review_packet["packet_mode"] == "safe"
    assert internal_packet["packet_mode"] == "full"
    assert "Can a VIP customer" not in serialized
    assert "Raw answer" not in serialized
    assert "Refunds after the deadline are not allowed." not in serialized
    assert "refund_policy.md#sec-1" not in serialized
    assert r"C:\customer\docs\VIP refund policy.md" not in serialized
    assert "VIP_REFUND_CASE" not in serialized
    assert "evidence_mismatch" in serialized
    assert review_packet["major_failures"][0]["case_id"] == ""
    assert review_packet["major_failures"][0]["case_id_hash"]
    assert review_packet["major_failures"][0]["safe_reason_code"] == "evidence_mismatch"
    assert internal_packet["major_failures"][0]["case_id"] == "VIP_REFUND_CASE"
    assert internal_packet["major_failures"][0]["question_summary"].startswith("Can a VIP customer")
    assert "Raw answer" in internal_packet["major_failures"][0]["actual_summary"]
    assert internal_packet["document_corpus"]["target_documents"][0]["source_path"] == (
        r"C:\customer\docs\VIP refund policy.md"
    )


def test_customer_review_markdown_contains_only_safe_delivery_information() -> None:
    packet = build_review_packet_safe(_review_packet_artifacts(report_mode="ci"))
    markdown = build_customer_review_markdown(packet)

    assert "レビュー種別: 納品後変更レビュー (`post_delivery_change`)" in markdown
    assert "情報として共有可能か: shareable" in markdown
    assert "正式提出として推奨されるか: not_recommended" in markdown
    assert "このレポートは正式な顧客提出レポートとしては推奨されません。" in markdown
    assert "リリース承認前に担当者レビューへ回してください。" in markdown
    assert "S1: evidence_mismatch" in markdown
    assert "Raw answer" not in markdown
    assert "Can a VIP customer" not in markdown
    assert "refund_policy.md#sec-1" not in markdown
    assert "C:\\customer\\docs" not in markdown
    assert "ACME policy owner" not in markdown


def test_customer_review_markdown_keeps_old_unknown_stage_title_fallback() -> None:
    markdown = build_customer_review_markdown({"review_stage": "unknown"})

    assert markdown.startswith("# Customer Review")


def test_release_decision_schema_validates_minimal_record() -> None:
    decision = ReleaseDecision(
        decision="conditional",
        decided_by="",
        reviewer_role="partner_pm",
        unresolved_blockers=["failure-abc123"],
        required_actions=["Fix and rerun."],
    )

    assert decision.decision == "conditional"
    assert decision.unresolved_blockers == ["failure-abc123"]


def test_production_readiness_not_ready_for_critical_failure_and_no_go() -> None:
    packet = build_review_packet_safe(_review_packet_artifacts(report_mode="ci"))
    blocker_codes = {item.code for item in packet.production_readiness.blockers}

    assert packet.production_readiness.status == "not_ready"
    assert "critical_failure_remaining" in blocker_codes
    assert "no_go_decision" in blocker_codes


def test_production_readiness_warns_when_document_versions_are_missing() -> None:
    packet = build_review_packet_safe(
        _ready_review_packet_artifacts(report_mode="ci", include_versions=False)
    )
    warning_codes = {item.code for item in packet.production_readiness.warnings}

    assert packet.production_readiness.status == "conditional"
    assert "document_versions_missing" in warning_codes
    assert packet.customer_submission_readiness.status == "conditional"
    assert packet.delivery_review.status == "needs_approval"


def test_production_readiness_ready_when_required_inputs_are_present() -> None:
    packet = build_review_packet_safe(_ready_review_packet_artifacts(report_mode="ci"))

    assert packet.review_stage == "post_delivery_change"
    assert packet.production_readiness.status == "ready"
    assert packet.production_readiness.blockers == []
    assert packet.production_readiness.warnings == []
    assert packet.delivery_review.status == "deliverable"
    assert packet.customer_submission_readiness.status == "recommended"


def test_production_readiness_warns_when_affected_category_has_no_active_case() -> None:
    artifacts = _ready_review_packet_artifacts(
        report_mode="ci",
        affected_business_categories=["refund_policy", "cancellation"],
    )
    packet = build_review_packet_safe(artifacts)
    warning_codes = {item.code for item in packet.production_readiness.warnings}
    warning_reasons = [item.reason for item in packet.production_readiness.warnings]

    assert packet.decision.status == "pass"
    assert packet.production_readiness.status == "conditional"
    assert "case_coverage_missing" in warning_codes
    assert any("cancellation" in reason for reason in warning_reasons)
    assert not any("Can a customer request a refund" in reason for reason in warning_reasons)
    assert not any("Refunds are allowed" in reason for reason in warning_reasons)


def test_production_readiness_does_not_warn_when_affected_category_has_active_case() -> None:
    packet = build_review_packet_safe(
        _ready_review_packet_artifacts(
            report_mode="ci",
            affected_business_categories=["refund_policy"],
        )
    )
    warning_codes = {item.code for item in packet.production_readiness.warnings}

    assert "case_coverage_missing" not in warning_codes


def test_pre_delivery_does_not_emit_case_coverage_warning() -> None:
    packet = build_review_packet_safe(
        _ready_review_packet_artifacts(
            report_mode="ci",
            affected_business_categories=["cancellation"],
            review_stage="pre_delivery",
        )
    )
    warning_codes = {item.code for item in packet.production_readiness.warnings}

    assert packet.review_stage == "pre_delivery"
    assert "case_coverage_missing" not in warning_codes


def test_production_readiness_warns_when_affected_category_lacks_s1_s2_case() -> None:
    low_priority_case = QATestCase(
        case_id="REFUND_LOW_PRIORITY_CASE",
        name="Refund low priority case",
        question="Can a customer ask a refund status question?",
        severity="S3",
        expected_answer="Share the refund status workflow.",
        expected_evidence=["refund_policy.md#sec-3"],
        category="refund_policy",
        risk_domain="refund_policy",
        source_doc="refund_policy.md",
        updated_at="2026-05-01",
    )
    packet = build_review_packet_safe(
        _ready_review_packet_artifacts(
            report_mode="ci",
            affected_business_categories=["refund_policy"],
            active_cases=[low_priority_case],
        )
    )
    warning_codes = {item.code for item in packet.production_readiness.warnings}

    assert "case_coverage_missing" not in warning_codes
    assert "high_priority_case_coverage_missing" in warning_codes


def test_pre_delivery_accepts_missing_change_event_without_change_warning() -> None:
    packet = build_review_packet_safe(
        _ready_review_packet_artifacts(report_mode="ci", include_change_event=False)
    )
    warning_codes = {item.code for item in packet.production_readiness.warnings}

    assert packet.review_stage == "pre_delivery"
    assert "change_event_missing" not in warning_codes
    assert "change_type_unknown" not in warning_codes


def test_post_delivery_change_warns_when_change_event_is_missing() -> None:
    packet = build_review_packet_safe(
        _ready_review_packet_artifacts(
            report_mode="ci",
            include_change_event=False,
            review_stage="post_delivery_change",
        )
    )
    warning_codes = {item.code for item in packet.production_readiness.warnings}

    assert packet.production_readiness.status == "conditional"
    assert "change_event_missing" in warning_codes
    assert "change_type_unknown" in warning_codes


def test_production_readiness_warns_when_change_type_is_unknown() -> None:
    packet = build_review_packet_safe(
        _ready_review_packet_artifacts(report_mode="ci", change_type="custom_customer_change")
    )
    warning_codes = {item.code for item in packet.production_readiness.warnings}

    assert packet.production_readiness.status == "conditional"
    assert "change_type_unknown" in warning_codes


def test_production_readiness_warns_when_document_update_has_no_affected_documents() -> None:
    packet = build_review_packet_safe(
        _ready_review_packet_artifacts(
            report_mode="ci",
            include_affected_documents=False,
        )
    )
    warning_codes = {item.code for item in packet.production_readiness.warnings}

    assert packet.production_readiness.status == "conditional"
    assert "affected_documents_missing" in warning_codes


def test_production_readiness_blocks_when_source_of_truth_is_missing() -> None:
    packet = build_review_packet_safe(
        _ready_review_packet_artifacts(report_mode="ci", include_source_of_truth=False)
    )
    blocker_codes = {item.code for item in packet.production_readiness.blockers}

    assert packet.production_readiness.status == "not_ready"
    assert "source_of_truth_missing" in blocker_codes
