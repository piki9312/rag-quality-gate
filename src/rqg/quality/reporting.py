"""Gate report adapters for emitting reusable output artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Protocol

from rqg.domain import (
    BlockingReason,
    DecisionExplanation,
    Failure,
    GateDecision,
    ReviewPacket,
    map_customer_severity,
)
from rqg.quality.review_stage import normalize_review_stage
from rqg.security import sanitize_payload, sanitize_text

GATE_REPORT_SCHEMA_VERSION = "1.0"
CI_UNKNOWN_REASON_CODE = "unknown_failure"
CI_SAFE_REASON_CODES = {
    "answer_quality_below_threshold",
    "answer_quality_fail",
    "bad_json",
    "configuration_error",
    "embedding_fallback_used",
    "evaluation_error",
    "evidence_mismatch",
    "expected_evidence_recall_below_threshold",
    "judge_fallback_used",
    "judge_unavailable",
    "judge_unreliable",
    "keyword_match_below_threshold",
    "latency_fail",
    "needs_human_review",
    "overall_threshold_not_met",
    "provider_error",
    "retrieval_fail",
    "s1_case_failed",
    "s2_case_failed",
    "safety_fail",
    "schema_fail",
    "threshold_not_met",
    "timeout",
    CI_UNKNOWN_REASON_CODE,
}
CI_REASON_ALIASES = {
    "bad_reference": "evidence_mismatch",
    "condition_mismatch": "answer_quality_fail",
    "deadline_or_period_mismatch": "answer_quality_fail",
    "embedding_reliability": "embedding_fallback_used",
    "error": "evaluation_error",
    "exception_omission": "answer_quality_fail",
    "human_review": "needs_human_review",
    "insufficient_context": "expected_evidence_recall_below_threshold",
    "judge_fallback": "judge_fallback_used",
    "judge_reliability": "judge_unreliable",
    "keyword_miss": "keyword_match_below_threshold",
    "missing_evidence": "expected_evidence_recall_below_threshold",
    "negation_error": "answer_quality_fail",
    "numeric_mismatch": "answer_quality_fail",
    "over_assertive_answer": "answer_quality_fail",
    "policy_gap": "answer_quality_fail",
    "retrieval_miss": "retrieval_fail",
    "source_mismatch": "evidence_mismatch",
    "stale": "answer_quality_fail",
    "synthesis": "answer_quality_fail",
    "tool_failure": "provider_error",
    "unsupported_claim": "answer_quality_fail",
}


@dataclass(frozen=True, slots=True)
class GateReportArtifacts:
    markdown: str
    decision: GateDecision
    history_summary: dict[str, object]
    report_path: Path
    decision_path: Path
    history_summary_path: Path
    history_path: Path
    bundle_path: Path
    customer_summary_markdown: str = ""
    customer_summary_path: Path | None = None
    check_result: Any | None = None
    report_mode: str = "full"


class GateReportAdapter(Protocol):
    def emit(self, artifacts: GateReportArtifacts) -> Path | None: ...


class MarkdownFileReportAdapter:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def emit(self, artifacts: GateReportArtifacts) -> Path:
        return _write_text_output(self.path, artifacts.markdown)


class DecisionJsonReportAdapter:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def emit(self, artifacts: GateReportArtifacts) -> Path:
        if artifacts.report_mode == "ci":
            return _write_json_data_output(
                self.path,
                build_ci_safe_gate_decision_payload(artifacts.decision),
            )
        return _write_json_model_output(self.path, artifacts.decision)


class HistorySummaryJsonReportAdapter:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def emit(self, artifacts: GateReportArtifacts) -> Path:
        if artifacts.report_mode == "ci":
            return _write_json_data_output(
                self.path,
                build_ci_safe_history_summary_payload(artifacts.history_summary),
            )
        return _write_json_data_output(self.path, artifacts.history_summary)


class DecisionHistoryJsonlReportAdapter:
    def __init__(self, path: str | Path, *, enabled: bool = True):
        self.path = Path(path)
        self.enabled = enabled

    def emit(self, artifacts: GateReportArtifacts) -> Path | None:
        if not self.enabled:
            return None
        return _append_jsonl_output(self.path, artifacts.decision)


class BundleJsonReportAdapter:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def emit(self, artifacts: GateReportArtifacts) -> Path:
        return _write_json_data_output(self.path, build_gate_report_bundle_payload(artifacts))


def build_gate_report_bundle_payload(artifacts: GateReportArtifacts) -> dict[str, object]:
    """Build a consolidated machine-readable gate report bundle."""
    report_mode = str(getattr(artifacts, "report_mode", "full") or "full")
    decision_payload = (
        build_ci_safe_gate_decision_payload(artifacts.decision)
        if report_mode == "ci"
        else artifacts.decision.model_dump(mode="json")
    )
    history_summary = (
        build_ci_safe_history_summary_payload(artifacts.history_summary)
        if report_mode == "ci"
        else artifacts.history_summary
    )
    artifact_base_dir = artifacts.bundle_path.parent
    payload = {
        "schema_version": GATE_REPORT_SCHEMA_VERSION,
        "report_mode": report_mode,
        "decision": decision_payload,
        "history_summary": history_summary,
        "report_markdown": artifacts.markdown,
        "customer_summary_markdown": (
            "" if report_mode == "ci" else artifacts.customer_summary_markdown
        ),
        "artifact_paths": {
            "report_path": safe_relative_artifact_path(artifacts.report_path, artifact_base_dir),
            "customer_summary_path": (
                safe_relative_artifact_path(artifacts.customer_summary_path, artifact_base_dir)
                if artifacts.customer_summary_path is not None
                else ""
            ),
            "decision_path": safe_relative_artifact_path(
                artifacts.decision_path, artifact_base_dir
            ),
            "history_summary_path": safe_relative_artifact_path(
                artifacts.history_summary_path, artifact_base_dir
            ),
            "history_path": (
                ""
                if report_mode == "ci"
                else safe_relative_artifact_path(artifacts.history_path, artifact_base_dir)
            ),
            "bundle_path": safe_relative_artifact_path(artifacts.bundle_path, artifact_base_dir),
        },
    }

    cases: list[dict[str, object]] = []
    target_docs: list[str] = []
    summary = _build_bundle_summary_from_decision(artifacts.decision)
    overall_decision = _overall_decision_from_gate_decision(artifacts.decision)

    if artifacts.check_result is not None:
        from rqg.quality.check import (
            build_case_report_rows,
            build_ci_case_report_rows,
            build_customer_report_summary,
            collect_target_docs_if_report_mode_allows,
            map_overall_decision,
            normalize_report_mode,
        )

        normalized_report_mode = normalize_report_mode(report_mode)
        if normalized_report_mode == "ci":
            cases = build_ci_case_report_rows(artifacts.check_result)
        else:
            cases = build_case_report_rows(
                artifacts.check_result,
                report_mode=normalized_report_mode,
            )
        target_docs = collect_target_docs_if_report_mode_allows(
            artifacts.check_result,
            normalized_report_mode,
        )
        summary = build_customer_report_summary(artifacts.check_result)
        overall_decision = map_overall_decision(artifacts.check_result)

    payload.update(
        {
            "report_version": GATE_REPORT_SCHEMA_VERSION,
            "executed_at": decision_payload["created_at"],
            "client_name": (
                None if report_mode == "ci" else _resolve_client_name(artifacts.decision)
            ),
            "app_name": (None if report_mode == "ci" else _resolve_app_name(artifacts.decision)),
            "target_docs": target_docs,
            "change_event": (
                None if report_mode == "ci" else _extract_change_event(artifacts.decision)
            ),
            "summary": summary,
            "overall_decision": overall_decision,
            "cases": cases,
            "execution_mode": decision_payload.get("execution_mode"),
            "provenance": decision_payload.get("provenance", {}),
            "manual_review_summary": decision_payload.get("manual_review_summary", {}),
        }
    )
    payload["review_packet"] = build_review_packet(artifacts).model_dump(mode="json")
    payload["customer_review_markdown"] = build_customer_review_markdown(
        build_review_packet_safe(artifacts)
    )
    return payload


def build_review_packet(artifacts: GateReportArtifacts) -> ReviewPacket:
    """Build a ReviewPacket matching the artifact report mode."""
    if str(artifacts.report_mode or "full").strip().lower() == "full":
        return build_review_packet_full(artifacts)
    return build_review_packet_safe(artifacts)


def build_review_packet_safe(artifacts: GateReportArtifacts) -> ReviewPacket:
    """Build a safe ReviewPacket without raw questions, answers, or evidence text."""
    return _build_review_packet(artifacts, packet_mode="safe")


def build_review_packet_full(artifacts: GateReportArtifacts) -> ReviewPacket:
    """Build a full ReviewPacket for local/private/customer-controlled review."""
    return _build_review_packet(artifacts, packet_mode="full")


def _build_review_packet(artifacts: GateReportArtifacts, *, packet_mode: str) -> ReviewPacket:
    from rqg.quality.check import build_customer_report_summary, normalize_report_mode

    report_mode = normalize_report_mode(artifacts.report_mode)
    decision = artifacts.decision
    check_result = artifacts.check_result
    summary = (
        build_customer_report_summary(check_result)
        if check_result is not None
        else _build_bundle_summary_from_decision(decision)
    )
    total_cases = int(summary.get("total_cases") or decision.metrics.get("current_runs", 0) or 0)
    failed_cases = int(summary.get("failed_cases") or 0)
    passed_cases = int(summary.get("passed_cases") or max(0, total_cases - failed_cases))
    pass_rate = float(
        summary.get("overall_pass_rate") or decision.metrics.get("overall_pass_rate", 0.0) or 0.0
    )
    failures = _build_review_failures(artifacts, packet_mode=packet_mode)
    decision_explanation = _build_decision_explanation(decision, failures)
    scope = _build_review_scope(artifacts, packet_mode=packet_mode, report_mode=report_mode)
    change_summary = _build_change_summary(artifacts, packet_mode=packet_mode)
    review_stage = _infer_review_stage(decision, change_summary)
    document_corpus = _build_document_corpus(
        artifacts,
        packet_mode=packet_mode,
        report_mode=report_mode,
    )
    evidence_policy = _build_evidence_policy(packet_mode=packet_mode)
    production_readiness = _build_production_readiness(
        decision=decision,
        failures=failures,
        change_summary=change_summary,
        review_stage=review_stage,
        document_corpus=document_corpus,
        evidence_policy=evidence_policy,
    )
    blocking_items = _build_delivery_blocking_items(failures)
    customer_shareability = _build_customer_shareability(packet_mode=packet_mode)
    delivery_review = _build_delivery_review(
        decision=decision,
        failures=failures,
        blocking_items=blocking_items,
        production_readiness=production_readiness,
        customer_shareability=customer_shareability,
    )
    customer_submission_readiness = _build_customer_submission_readiness(
        delivery_review=delivery_review,
        production_readiness=production_readiness,
        customer_shareability=customer_shareability,
    )
    release_decision = _build_release_decision_stub(
        delivery_review=delivery_review,
        blocking_items=blocking_items,
    )
    return ReviewPacket(
        packet_mode=packet_mode,  # type: ignore[arg-type]
        review_stage=review_stage,  # type: ignore[arg-type]
        run_summary={
            "run_id": decision.run_id,
            "created_at": decision.created_at.isoformat(),
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "pass_rate": pass_rate,
            "report_mode": report_mode,
        },
        decision={
            "status": decision.status,
            "policy_status": decision.policy_status,
            "customer_status": _customer_status(decision),
            "needs_human_review": decision.needs_human_review,
        },
        decision_explanation=decision_explanation,
        scope=scope,
        change_summary=change_summary,
        document_corpus=document_corpus,
        severity_summary=_build_severity_summary(failures),
        risk_breakdown=_build_risk_breakdown(failures),
        major_failures=failures[:10],
        report_sections=_build_report_sections(
            decision=decision,
            summary=summary,
            failures=failures,
            change_summary=change_summary,
            scope=scope,
            document_corpus=document_corpus,
            production_readiness=production_readiness,
            delivery_review=delivery_review,
            customer_submission_readiness=customer_submission_readiness,
            review_stage=review_stage,
        ),
        evidence_policy=evidence_policy,
        production_readiness=production_readiness,
        delivery_review=delivery_review,
        blocking_items=blocking_items,
        customer_shareability=customer_shareability,
        customer_submission_readiness=customer_submission_readiness,
        release_decision=release_decision,
    )


def _build_review_failures(
    artifacts: GateReportArtifacts,
    *,
    packet_mode: str,
) -> list[Failure]:
    check_result = artifacts.check_result
    if check_result is None:
        return []

    case_by_id = {case.case_id: case for case in getattr(check_result, "active_cases", [])}
    rows: list[Failure] = []
    for record in sorted(
        getattr(check_result, "current_records", []),
        key=lambda item: (
            0 if str(getattr(item, "severity", "")).upper() == "S1" and not item.passed else 1,
            0 if not item.passed else 1,
            str(getattr(item, "case_id", "")),
        ),
    ):
        if record.passed and not (
            record.judge_fallback_used or record.embedding_fallback_used
        ):
            continue
        case = case_by_id.get(record.case_id)
        failure_category = str(record.failure_category or record.failure_type or "").strip()
        pattern = _extract_failure_pattern(getattr(case, "notes", "") if case else "")
        business_category = str(
            (getattr(case, "risk_domain", "") if case else "")
            or (getattr(case, "category", "") if case else "")
            or record.risk_domain
            or record.category
            or ""
        )
        human_review_required = bool(
            record.judge_fallback_used
            or record.embedding_fallback_used
            or (str(record.severity).upper() == "S1" and not record.passed)
        )
        customer_severity = map_customer_severity(
            internal_severity=record.severity,
            failure_category=failure_category,
            failure_type=record.failure_type,
            business_category=business_category,
            required_action=(
                getattr(case, "required_action", "")
                if case
                else record.required_action
            ),
            human_review_required=human_review_required,
        )
        safe_reason_code = _safe_ci_reason_code(failure_category or record.failure_type)
        exposed_failure_category = (
            failure_category
            if packet_mode == "full"
            else safe_reason_code or CI_UNKNOWN_REASON_CODE
        )
        exposed_business_category = business_category if packet_mode == "full" else ""
        rows.append(
            Failure(
                failure_id=f"failure-{stable_case_ref(record.case_id)}",
                case_id=record.case_id if packet_mode == "full" else "",
                case_id_hash=stable_case_ref(record.case_id),
                customer_severity=customer_severity,
                internal_severity=str(record.severity or ""),
                failure_category=exposed_failure_category,
                failure_pattern=pattern if packet_mode == "full" else "",
                business_category=exposed_business_category,
                go_no_go_impact=_failure_go_no_go_impact(
                    record=record,
                    customer_severity=customer_severity,
                    human_review_required=human_review_required,
                ),
                human_review_required=human_review_required,
                question_summary=(
                    str(getattr(case, "question", "") or "") if packet_mode == "full" else ""
                ),
                expected_summary=(
                    str(getattr(case, "expected_answer", "") or "")
                    if packet_mode == "full"
                    else ""
                ),
                actual_summary=str(record.answer or "") if packet_mode == "full" else "",
                evidence_status=_evidence_status(record),
                safe_reason_code=safe_reason_code or CI_UNKNOWN_REASON_CODE,
                next_action=_failure_next_action(
                    record=record,
                    failure_category=failure_category,
                    human_review_required=human_review_required,
                ),
                suggested_fix=_failure_suggested_fix(failure_category),
                full_detail_ref=(
                    f"case:{record.case_id}"
                    if packet_mode == "full"
                    else f"case:{stable_case_ref(record.case_id)}"
                ),
            )
        )
    return rows


def stable_case_ref(case_id: object) -> str:
    return hashlib.sha256(str(case_id or "").encode("utf-8")).hexdigest()[:16]


def _extract_failure_pattern(notes: object) -> str:
    for token in str(notes or "").replace(";", " ").split():
        if token.startswith("pattern:"):
            return token.split(":", 1)[1]
    return ""


def _failure_go_no_go_impact(
    *,
    record: object,
    customer_severity: str,
    human_review_required: bool,
) -> str:
    if not getattr(record, "passed", True) and customer_severity in {"Critical", "High"}:
        return "blocks_release"
    if human_review_required:
        return "requires_human_review"
    if not getattr(record, "passed", True):
        return "needs_fix_or_review"
    return "informational"


def _evidence_status(record: object) -> str:
    if (
        getattr(record, "evidence_match", None) is True
        or getattr(record, "retrieval_hit", None) is True
    ):
        return "aligned"
    if (
        getattr(record, "evidence_match", None) is False
        or getattr(record, "retrieval_hit", None) is False
    ):
        return "mismatch"
    if getattr(record, "retrieved_ids", None):
        return "retrieved_unverified"
    return "not_available"


def _failure_next_action(
    *,
    record: object,
    failure_category: str,
    human_review_required: bool,
) -> str:
    if human_review_required:
        return "Route for human review before release approval."
    if failure_category:
        return f"Investigate and fix {failure_category} before rerun."
    if not getattr(record, "passed", True):
        return "Investigate failed case and rerun the gate."
    return "No immediate action required."


def _failure_suggested_fix(failure_category: str) -> str:
    category = str(failure_category or "").strip().lower()
    if category in {"retrieval_miss", "missing_evidence", "insufficient_context"}:
        return "Review source documents, expected evidence, and retrieval settings."
    if category in {"source_mismatch", "bad_reference", "evidence_mismatch"}:
        return "Align the answer with the approved source document evidence."
    if category in {"keyword_miss", "answer_quality_fail", "synthesis"}:
        return "Update prompt, response policy, or expected answer handling and retest."
    if category in {"judge_fallback", "judge_reliability"}:
        return "Re-run with judge reliability restored and confirm manually."
    return "Review the failed case, apply the required fix, and rerun."


def _build_decision_explanation(
    decision: GateDecision,
    failures: list[Failure],
) -> DecisionExplanation:
    blocking_reasons = _build_blocking_reasons(decision, failures)
    required_actions = [item.action for item in decision.next_actions[:5]]
    if decision.needs_human_review and not required_actions:
        required_actions.append("Route this run for human review before release approval.")
    return DecisionExplanation(
        headline=_decision_headline(decision),
        decision=_customer_status(decision),
        plain_language_reason=_plain_language_reason(decision, blocking_reasons),
        blocking_reasons=blocking_reasons,
        required_actions=required_actions,
    )


def _build_blocking_reasons(
    decision: GateDecision,
    failures: list[Failure],
) -> list[BlockingReason]:
    counts: dict[str, int] = {}
    severity_by_code: dict[str, str] = {}
    for failure in failures:
        code = failure.safe_reason_code or CI_UNKNOWN_REASON_CODE
        counts[code] = counts.get(code, 0) + 1
        if code not in severity_by_code or failure.customer_severity == "Critical":
            severity_by_code[code] = failure.customer_severity
    for code in decision.reason_codes:
        safe_code = _safe_ci_reason_code(code) or CI_UNKNOWN_REASON_CODE
        counts.setdefault(safe_code, 0)
        severity_by_code.setdefault(safe_code, _severity_for_reason_code(safe_code))
    if decision.policy_status == "block":
        counts.setdefault("s1_case_failed", int(decision.metrics.get("s1_fail_count", 0) or 0))
        severity_by_code.setdefault("s1_case_failed", "Critical")
    if decision.needs_human_review:
        counts.setdefault("needs_human_review", 1)
        severity_by_code.setdefault("needs_human_review", "High")

    rows: list[BlockingReason] = []
    for code, count in sorted(counts.items()):
        if code in {"", "unknown"}:
            continue
        rows.append(
            BlockingReason(
                reason_code=code,
                label=_reason_label(code),
                severity=severity_by_code.get(code, "Medium"),  # type: ignore[arg-type]
                affected_count=max(0, int(count or 0)),
                why_it_blocks=_why_reason_blocks(code),
            )
        )
    return rows


def _severity_for_reason_code(code: str) -> str:
    if code in {"s1_case_failed", "safety_fail"}:
        return "Critical"
    if code in {"needs_human_review", "judge_fallback_used", "judge_unavailable"}:
        return "High"
    return "Medium"


def _reason_label(code: str) -> str:
    labels = {
        "s1_case_failed": "Critical case failed",
        "s2_case_failed": "Non-critical case failed",
        "evidence_mismatch": "Evidence mismatch",
        "expected_evidence_recall_below_threshold": "Expected evidence not sufficiently retrieved",
        "keyword_match_below_threshold": "Expected answer elements missing",
        "needs_human_review": "Human review required",
        "judge_fallback_used": "Judge fallback used",
        "judge_unavailable": "Judge unavailable",
        "overall_threshold_not_met": "Overall threshold not met",
        "retrieval_fail": "Retrieval failure",
        "answer_quality_fail": "Answer quality issue",
        "unknown_failure": "Unclassified failure",
    }
    return labels.get(code, code.replace("_", " ").title())


def _why_reason_blocks(code: str) -> str:
    if code == "s1_case_failed":
        return "A high-risk case failed, so release should not proceed without correction."
    if code == "needs_human_review":
        return "The run includes reliability or review signals that require a human decision."
    if code in {"evidence_mismatch", "expected_evidence_recall_below_threshold", "retrieval_fail"}:
        return "The answer cannot be sufficiently tied to the expected source evidence."
    if code == "overall_threshold_not_met":
        return "The configured overall quality threshold was not met."
    return "This issue affects release confidence and should be reviewed before approval."


def _decision_headline(decision: GateDecision) -> str:
    customer_status = _customer_status(decision)
    if customer_status == "No-Go":
        return "No-Go: release should wait until blocking issues are fixed."
    if customer_status == "Needs Human Review":
        return "Needs human review before release approval."
    if customer_status == "Conditional":
        return "Conditional: review warnings and residual risk before release."
    return "Go: configured checks passed for this scoped run."


def _plain_language_reason(
    decision: GateDecision,
    blocking_reasons: list[BlockingReason],
) -> str:
    if blocking_reasons:
        top = blocking_reasons[0]
        return f"{top.label} is the primary release concern for this run."
    if decision.policy_status == "pass":
        return "The configured checks passed for the specified cases, documents, and settings."
    return "The run requires review before it can be used as release evidence."


def _customer_status(decision: GateDecision) -> str:
    if decision.policy_status == "block":
        return "No-Go"
    if decision.policy_status == "needs_human_review":
        return "Needs Human Review"
    if decision.policy_status == "warn" or decision.status == "warn":
        return "Conditional"
    if decision.status == "fail":
        return "Needs Human Review"
    return "Go"


def _build_review_scope(
    artifacts: GateReportArtifacts,
    *,
    packet_mode: str,
    report_mode: str,
) -> dict[str, object]:
    decision = artifacts.decision
    provenance = decision.provenance or {}
    if packet_mode == "safe":
        target_docs: list[str] = []
        change_event: object | None = None
    else:
        target_docs = _target_docs_from_check_result(
            artifacts.check_result,
            report_mode=report_mode,
        )
        change_event = _extract_change_event(decision) or provenance.get("change_event")
    if packet_mode == "safe":
        document_versions: list[str] = []
    else:
        document_versions = [
            str(value)
            for value in (
                provenance.get("doc_snapshot_ids")
                or ([provenance.get("index_version")] if provenance.get("index_version") else [])
            )
            if str(value).strip()
        ]
    return {
        "target_name": "" if packet_mode == "safe" else (_resolve_app_name(decision) or ""),
        "target_type": "customer_facing_ai",
        "target_documents": target_docs,
        "document_versions": document_versions,
        "change_event": change_event,
    }


def _target_docs_from_check_result(check_result: object, *, report_mode: str) -> list[str]:
    if check_result is None:
        return []
    try:
        from rqg.quality.check import collect_target_docs_if_report_mode_allows

        return collect_target_docs_if_report_mode_allows(check_result, report_mode)
    except Exception:
        return []


CHANGE_TYPES = {
    "chunking_change",
    "config_change",
    "document_update",
    "embedding_change",
    "model_change",
    "prompt_change",
    "retriever_change",
    "unknown",
}


def _build_change_summary(
    artifacts: GateReportArtifacts,
    *,
    packet_mode: str,
) -> dict[str, object]:
    decision = artifacts.decision
    provenance = decision.provenance or {}
    raw_change_event = _raw_change_event(decision, provenance)
    event = raw_change_event if isinstance(raw_change_event, dict) else {}
    active_cases = list(getattr(artifacts.check_result, "active_cases", []) or [])
    change_type = _safe_change_type(event.get("change_type"))
    changed_assets = _changed_asset_labels(event.get("changed_assets"))
    affected_documents = _string_list(event.get("affected_documents"))
    affected_categories = _string_list(event.get("affected_business_categories"))
    if not affected_categories:
        affected_categories = _unique_non_empty(
            [
                str(getattr(case, "risk_domain", "") or getattr(case, "category", "") or "")
                for case in active_cases
            ]
        )
    change_id = str(
        event.get("change_id")
        or event.get("change_event_id")
        or provenance.get("change_event_id")
        or ""
    ).strip()
    if packet_mode != "full":
        return {
            "change_type": change_type,
            "change_id": "",
            "change_id_hash": stable_case_ref(change_id) if change_id else "",
            "changed_assets_count": len(changed_assets),
            "affected_documents_count": len(affected_documents),
            "affected_business_categories": [],
            "target_release": "",
            "change_summary": (
                "Change event metadata is available."
                if raw_change_event is not None
                else ""
            ),
            "retest_reason": _safe_retest_reason(change_type, raw_change_event),
            "changed_assets": [],
            "affected_documents": [],
        }
    return {
        "change_type": change_type,
        "change_id": change_id,
        "change_id_hash": stable_case_ref(change_id) if change_id else "",
        "changed_assets_count": len(changed_assets),
        "affected_documents_count": len(affected_documents),
        "affected_business_categories": affected_categories,
        "target_release": str(event.get("target_release") or "").strip(),
        "change_summary": str(event.get("change_summary") or event.get("summary") or "").strip(),
        "retest_reason": str(
            event.get("retest_reason") or _safe_retest_reason(change_type, raw_change_event)
        ),
        "changed_assets": changed_assets,
        "affected_documents": affected_documents,
    }


def _raw_change_event(decision: GateDecision, provenance: dict[str, object]) -> object | None:
    return provenance.get("change_event") or _extract_change_event(decision)


def _infer_review_stage(decision: GateDecision, change_summary: dict[str, object]) -> str:
    provenance = decision.provenance or {}
    explicit = _normalize_stage(
        provenance.get("review_stage")
        or provenance.get("usage_stage")
        or provenance.get("review_context")
    )
    if explicit != "unknown":
        return explicit
    has_change = bool(
        change_summary.get("change_id")
        or change_summary.get("change_id_hash")
        or int(change_summary.get("changed_assets_count") or 0) > 0
        or int(change_summary.get("affected_documents_count") or 0) > 0
        or str(change_summary.get("change_type") or "unknown") != "unknown"
    )
    return "post_delivery_change" if has_change else "pre_delivery"


def _normalize_stage(value: object) -> str:
    return normalize_review_stage(value, allow_unknown=True)


def _customer_report_title(review_stage: str) -> str:
    if review_stage == "pre_delivery":
        return "AI回答品質診断レポート"
    if review_stage == "post_delivery_change":
        return "変更後品質確認レポート"
    if review_stage == "monthly_review":
        return "月次AI回答品質レビュー"
    return "Customer Review"


def _safe_change_type(value: object) -> str:
    item = str(value or "").strip().lower()
    return item if item in CHANGE_TYPES else "unknown"


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return _unique_non_empty([str(item or "") for item in value])
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _changed_asset_labels(value: object) -> list[str]:
    if not isinstance(value, list):
        return _string_list(value)
    rows: list[str] = []
    for item in value:
        if isinstance(item, str):
            rows.append(item)
        elif isinstance(item, dict):
            label = " ".join(
                str(item.get(key) or "").strip()
                for key in ("type", "name", "version", "path", "content_hash")
                if str(item.get(key) or "").strip()
            )
            rows.append(label)
    return _unique_non_empty(rows)


def _safe_retest_reason(change_type: str, raw_change_event: object | None) -> str:
    if raw_change_event is None:
        return ""
    if change_type == "document_update":
        return "Document update can change retrieval evidence and answer behavior."
    if change_type == "prompt_change":
        return "Prompt change can change answer policy and tone."
    if change_type == "model_change":
        return "Model change can alter answer generation behavior."
    if change_type in {"retriever_change", "chunking_change", "embedding_change"}:
        return "Retrieval configuration change can alter available evidence."
    return "Change event requires scoped retesting before release."


def _build_document_corpus(
    artifacts: GateReportArtifacts,
    *,
    packet_mode: str,
    report_mode: str,
) -> dict[str, object]:
    decision = artifacts.decision
    provenance = decision.provenance or {}
    target_docs = _target_docs_from_check_result(
        artifacts.check_result,
        report_mode=report_mode,
    )
    active_cases = list(getattr(artifacts.check_result, "active_cases", []) or [])
    source_docs = _unique_non_empty(
        [str(getattr(case, "source_doc", "") or "") for case in active_cases]
    )
    document_count = len(target_docs) if packet_mode == "full" else len(source_docs)
    version_values = _document_version_values(provenance)
    stale_policy = str(provenance.get("stale_doc_policy") or "").strip()
    source_of_truth = str(provenance.get("source_of_truth") or "").strip()
    source_of_truth_type = _source_of_truth_type(provenance, source_of_truth)
    has_source_of_truth = _has_declared_source_of_truth(provenance, source_of_truth)
    if packet_mode != "full":
        return {
            "document_count": document_count,
            "source_of_truth_type": source_of_truth_type,
            "stale_doc_policy": stale_policy,
            "stale_doc_policy_required": _stale_doc_policy_required(provenance),
            "version_hashes": [stable_case_ref(value) for value in version_values],
            "has_document_versions": bool(version_values),
            "has_source_of_truth": has_source_of_truth,
            "has_stale_doc_policy": bool(stale_policy),
            "target_documents": [],
            "source_of_truth": "",
            "affected_business_categories": [],
            "affected_cases": [],
        }

    case_by_doc: dict[str, list[object]] = {}
    for case in active_cases:
        source_doc = str(getattr(case, "source_doc", "") or "").strip()
        if source_doc:
            case_by_doc.setdefault(source_doc, []).append(case)
    document_rows = []
    for source_doc in source_docs:
        cases = case_by_doc.get(source_doc, [])
        first_case = cases[0] if cases else None
        document_rows.append(
            {
                "document_id": stable_case_ref(source_doc),
                "title": _source_doc_title(source_doc),
                "version": _case_document_version(first_case, version_values),
                "content_hash": "",
                "snapshot_id": _snapshot_id_for_doc(source_doc, provenance),
                "last_updated_at": str(getattr(first_case, "updated_at", "") or ""),
                "owner": str(getattr(first_case, "owner", "") or ""),
                "source_path": source_doc,
            }
        )
    affected_categories = _unique_non_empty(
        [
            str(getattr(case, "risk_domain", "") or getattr(case, "category", "") or "")
            for case in active_cases
        ]
    )
    affected_cases = _unique_non_empty(
        [str(getattr(case, "case_id", "") or "") for case in active_cases]
    )
    return {
        "document_count": len(document_rows),
        "source_of_truth_type": source_of_truth_type,
        "stale_doc_policy": stale_policy,
        "stale_doc_policy_required": _stale_doc_policy_required(provenance),
        "version_hashes": [stable_case_ref(value) for value in version_values],
        "has_document_versions": bool(
            version_values or any(row["version"] for row in document_rows)
        ),
        "has_source_of_truth": has_source_of_truth,
        "has_stale_doc_policy": bool(stale_policy),
        "target_documents": document_rows,
        "source_of_truth": source_of_truth,
        "affected_business_categories": affected_categories,
        "affected_cases": affected_cases,
    }


def _document_version_values(provenance: dict[str, object]) -> list[str]:
    raw_values = provenance.get("doc_snapshot_ids") or []
    if not isinstance(raw_values, list):
        raw_values = [raw_values]
    if not raw_values and provenance.get("index_version"):
        raw_values = [provenance.get("index_version")]
    return _unique_non_empty([str(value or "") for value in raw_values])


def _source_of_truth_type(provenance: dict[str, object], source_of_truth: str) -> str:
    raw_type = str(provenance.get("source_of_truth_type") or "").strip()
    if raw_type:
        return raw_type
    if source_of_truth:
        return "declared_source_of_truth"
    if provenance.get("doc_snapshot_ids"):
        return "document_snapshot"
    if provenance.get("index_version"):
        return "index_version"
    return "unknown"


def _has_declared_source_of_truth(provenance: dict[str, object], source_of_truth: str) -> bool:
    return bool(source_of_truth or str(provenance.get("source_of_truth_type") or "").strip())


def _stale_doc_policy_required(provenance: dict[str, object]) -> bool:
    value = provenance.get("stale_doc_policy_required")
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "required"}


def _case_document_version(case: object, version_values: list[str]) -> str:
    if case is not None:
        for attr in ("document_version", "updated_at", "last_reviewed_at"):
            value = str(getattr(case, attr, "") or "").strip()
            if value:
                return value
    return version_values[0] if version_values else ""


def _source_doc_title(source_doc: str) -> str:
    value = str(source_doc or "").strip()
    if "\\" in value:
        return PureWindowsPath(value).name
    return Path(value).name


def _snapshot_id_for_doc(source_doc: str, provenance: dict[str, object]) -> str:
    doc_snapshot_ids = provenance.get("doc_snapshot_ids") or []
    if isinstance(doc_snapshot_ids, list) and len(doc_snapshot_ids) == 1:
        return str(doc_snapshot_ids[0] or "")
    doc_snapshot_map = provenance.get("doc_snapshot_map") or {}
    if isinstance(doc_snapshot_map, dict):
        return str(doc_snapshot_map.get(source_doc) or "")
    return ""


def _unique_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        rows.append(item)
    return rows


def _build_severity_summary(failures: list[Failure]) -> dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for failure in failures:
        key = failure.customer_severity.lower()
        counts[key] = counts.get(key, 0) + 1
    return counts


def _build_risk_breakdown(failures: list[Failure]) -> dict[str, int]:
    counts = {
        "major_misguidance": 0,
        "evidence_mismatch": 0,
        "stale_reference": 0,
        "business_rule_violation": 0,
        "human_review_required": 0,
    }
    for failure in failures:
        text = " ".join(
            [
                failure.failure_category,
                failure.failure_pattern,
                failure.business_category,
                failure.safe_reason_code,
            ]
        ).lower()
        if any(term in text for term in ("answer_quality", "unsupported", "misguidance")):
            counts["major_misguidance"] += 1
        if any(term in text for term in ("evidence", "source", "retrieval")):
            counts["evidence_mismatch"] += 1
        if "stale" in text:
            counts["stale_reference"] += 1
        if any(term in text for term in ("policy", "billing", "refund", "cancel", "contract")):
            counts["business_rule_violation"] += 1
        if failure.human_review_required:
            counts["human_review_required"] += 1
    return counts


def _build_report_sections(
    *,
    decision: GateDecision,
    summary: dict[str, object],
    failures: list[Failure],
    change_summary: dict[str, object],
    scope: dict[str, object],
    document_corpus: dict[str, object] | None = None,
    production_readiness: dict[str, object] | None = None,
    delivery_review: dict[str, object] | None = None,
    customer_submission_readiness: dict[str, object] | None = None,
    review_stage: str = "unknown",
) -> dict[str, str]:
    customer_status = _customer_status(decision)
    critical_or_high = [
        failure
        for failure in failures
        if failure.customer_severity in {"Critical", "High"}
    ]
    corpus = document_corpus or {}
    corpus_summary = (
        f"document_count={corpus.get('document_count', 0)}; "
        f"source_of_truth_type={corpus.get('source_of_truth_type', 'unknown')}; "
        f"has_versions={corpus.get('has_document_versions', False)}; "
        f"stale_doc_policy={corpus.get('stale_doc_policy') or '-'}"
    )
    readiness = production_readiness or {}
    delivery = delivery_review or {}
    submission = customer_submission_readiness or {}
    change_section = (
        f"change_type={change_summary.get('change_type', 'unknown')}; "
        f"changed_assets={change_summary.get('changed_assets_count', 0)}; "
        f"affected_documents={change_summary.get('affected_documents_count', 0)}; "
        f"retest_reason={change_summary.get('retest_reason') or '-'}"
    )
    return {
        "report_title": _customer_report_title(review_stage),
        "executive_summary": _decision_headline(decision),
        "decision": f"{customer_status} ({decision.policy_status})",
        "change_summary": change_section,
        "scope": (
            f"Run {decision.run_id}; target_type={scope.get('target_type')}; "
            f"documents={len(scope.get('target_documents') or [])}; "
            f"corpus=({corpus_summary})"
        ),
        "production_readiness": str(
            readiness.get("readiness_summary") or "Production readiness is not available."
        ),
        "delivery_review": str(
            delivery.get("summary") or "Delivery review summary is not available."
        )
        + f" Customer submission readiness={submission.get('status', 'not_recommended')}.",
        "customer_submission": str(
            submission.get("recommendation") or "Formal customer submission is not recommended."
        ),
        "major_risks": (
            f"{len(critical_or_high)} Critical/High issue(s); "
            f"main category={summary.get('main_failure_category') or '-'}"
        ),
        "blocking_issues": "; ".join(
            f"{failure.customer_severity}: {failure.safe_reason_code}"
            for failure in critical_or_high[:5]
        ),
        "required_actions": "; ".join(item.action for item in decision.next_actions[:5]),
        "residual_risks": (
            "PASS is scoped to configured cases and does not guarantee all answers."
        ),
        "disclaimer": (
            "This packet supports release review; it is not a complete guarantee "
            "of AI answer quality."
        ),
    }


def _build_delivery_blocking_items(failures: list[Failure]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for failure in failures:
        severity = str(failure.internal_severity or "").upper()
        blocks_delivery = bool(
            severity == "S1"
            or failure.customer_severity in {"Critical", "High"}
            or failure.go_no_go_impact in {"blocks_release", "requires_human_review"}
        )
        if severity not in {"S1", "S2"} and not blocks_delivery:
            continue
        rows.append(
            {
                "item_id": failure.failure_id or f"failure-{failure.case_id_hash}",
                "severity": severity or failure.customer_severity,
                "issue": failure.safe_reason_code or CI_UNKNOWN_REASON_CODE,
                "category": failure.safe_reason_code or CI_UNKNOWN_REASON_CODE,
                "blocks_delivery": blocks_delivery,
                "required_action": failure.next_action
                or "Review the unresolved item before customer submission.",
                "owner": "",
                "due_date": "",
                "status": "open",
            }
        )
    return rows


def _build_customer_shareability(*, packet_mode: str) -> dict[str, object]:
    if packet_mode == "safe":
        return {
            "status": "shareable",
            "reasons": ["safe_review_packet"],
            "forbidden_fields_detected": [],
            "safe_mode_required": True,
        }
    return {
        "status": "needs_review",
        "reasons": ["full_packet_requires_safe_export_before_customer_submission"],
        "forbidden_fields_detected": ["full_evidence_mode"],
        "safe_mode_required": True,
    }


def _build_delivery_review(
    *,
    decision: GateDecision,
    failures: list[Failure],
    blocking_items: list[dict[str, object]],
    production_readiness: dict[str, object],
    customer_shareability: dict[str, object],
) -> dict[str, object]:
    unresolved_s1_count = sum(
        1 for item in blocking_items if str(item.get("severity", "")).upper() == "S1"
    )
    unresolved_s2_count = sum(
        1 for item in blocking_items if str(item.get("severity", "")).upper() == "S2"
    )
    blocking_delivery_count = sum(1 for item in blocking_items if item.get("blocks_delivery"))
    readiness_status = str(production_readiness.get("status") or "unknown")
    shareability_status = str(customer_shareability.get("status") or "needs_review")

    if _customer_status(decision) == "No-Go" or blocking_delivery_count:
        status = "not_deliverable"
    elif readiness_status == "not_ready":
        status = "needs_fix"
    elif decision.needs_human_review or readiness_status == "conditional":
        status = "needs_approval"
    elif shareability_status != "shareable":
        status = "needs_approval"
    elif failures:
        status = "needs_approval"
    else:
        status = "deliverable"

    if shareability_status == "shareable":
        customer_submission_status = "safe_to_share"
    elif shareability_status == "not_shareable":
        customer_submission_status = "not_safe"
    else:
        customer_submission_status = "needs_review"

    required_actions = [
        str(item.get("required_action") or "").strip()
        for item in blocking_items
        if str(item.get("required_action") or "").strip()
    ]
    required_actions.extend(
        str(action).strip()
        for action in production_readiness.get("required_actions", [])
        if str(action).strip()
    )
    required_actions = _unique_non_empty(required_actions)
    if customer_submission_status != "safe_to_share":
        required_actions.append("Review customer-facing export before submission.")

    return {
        "status": status,
        "summary": _delivery_review_summary(
            status=status,
            unresolved_s1_count=unresolved_s1_count,
            unresolved_s2_count=unresolved_s2_count,
            customer_submission_status=customer_submission_status,
        ),
        "unresolved_s1_count": unresolved_s1_count,
        "unresolved_s2_count": unresolved_s2_count,
        "blockers": blocking_items,
        "customer_submission_status": customer_submission_status,
        "required_actions": required_actions,
        "reviewer_notes_placeholder": (
            "Reviewer notes: record approval, rejection, accepted risk, or required fixes here."
        ),
    }


def _build_customer_submission_readiness(
    *,
    delivery_review: dict[str, object],
    production_readiness: dict[str, object],
    customer_shareability: dict[str, object],
) -> dict[str, object]:
    reasons: list[str] = []
    shareability_status = str(customer_shareability.get("status") or "needs_review")
    delivery_status = str(delivery_review.get("status") or "unknown")
    readiness_status = str(production_readiness.get("status") or "unknown")
    unresolved_s1 = int(delivery_review.get("unresolved_s1_count") or 0)

    if shareability_status != "shareable":
        reasons.append("safe_export_not_confirmed")
        return {
            "status": "not_recommended",
            "reasons": reasons,
            "recommendation": (
                "Do not submit this as a formal customer report until the safe export is reviewed."
            ),
        }

    if delivery_status == "not_deliverable" or readiness_status == "not_ready" or unresolved_s1:
        reasons.append("unresolved_blockers_or_no_go")
        return {
            "status": "not_recommended",
            "reasons": reasons,
            "recommendation": (
                "Formal customer submission is not recommended. Use this only as an interim "
                "safe draft if the PoC agreement requires shared findings."
            ),
        }

    if delivery_status in {"needs_approval", "needs_fix"} or readiness_status == "conditional":
        reasons.append("conditional_or_pm_approval_required")
        return {
            "status": "conditional",
            "reasons": reasons,
            "recommendation": (
                "Formal customer submission is conditional on PM approval and documented residual risk."
            ),
        }

    reasons.append("no_unresolved_blockers_detected")
    return {
        "status": "recommended",
        "reasons": reasons,
        "recommendation": (
            "Formal customer submission is recommended for the scoped quality review."
        ),
    }


def _delivery_review_summary(
    *,
    status: str,
    unresolved_s1_count: int,
    unresolved_s2_count: int,
    customer_submission_status: str,
) -> str:
    if status == "deliverable":
        return "Delivery review indicates this safe packet is ready for customer submission."
    if status == "not_deliverable":
        return (
            "Delivery is not recommended until unresolved blocking items are fixed or formally "
            f"accepted. S1={unresolved_s1_count}, S2={unresolved_s2_count}."
        )
    if status == "needs_fix":
        return "Fix production readiness blockers before treating this run as deliverable."
    if status == "needs_approval":
        return (
            "Delivery may proceed only after PM/customer approval of remaining warnings and "
            f"customer submission status={customer_submission_status}."
        )
    return "Delivery review status is unknown."


def _build_release_decision_stub(
    *,
    delivery_review: dict[str, object],
    blocking_items: list[dict[str, object]],
) -> dict[str, object]:
    status = str(delivery_review.get("status") or "unknown")
    if status == "deliverable":
        decision = "approved"
    elif status == "not_deliverable":
        decision = "rejected"
    elif status in {"needs_approval", "needs_fix"}:
        decision = "needs_review"
    else:
        decision = "needs_review"
    unresolved = [
        str(item.get("item_id") or "")
        for item in blocking_items
        if str(item.get("status") or "open") == "open"
    ]
    return {
        "decision": decision,
        "decided_by": "",
        "decided_at": "",
        "reviewer_role": "",
        "accepted_risks": [],
        "unresolved_blockers": _unique_non_empty(unresolved),
        "required_actions": list(delivery_review.get("required_actions", []) or []),
        "evidence_refs": [],
        "notes": "",
    }


def _customer_action_text(action: object) -> str:
    raw = str(action or "").strip()
    translations = {
        "Route for human review before release approval.": "リリース承認前に担当者レビューへ回してください。",
        "Route this run for human review before release approval.": "リリース承認前にこの実行結果を担当者レビューへ回してください。",
        "Fix the Critical failure(s) and rerun before production release.": "本番リリース前にCriticalの失敗を修正し、再実行してください。",
        "Resolve blocking issues and rerun the gate.": "ブロッカーを解消し、gateを再実行してください。",
        "Define the source of truth for the document corpus.": "文書コーパスの正本となる文書を定義してください。",
        "Define how stale documents are rejected, flagged, or reviewed.": "古い文書を拒否、警告、レビュー対象のいずれで扱うか定義してください。",
        "Complete human review before treating this run as release evidence.": "この実行結果をリリース判断の証跡として扱う前に、人間レビューを完了してください。",
        "Record affected documents or document count for the ChangeEvent.": "ChangeEventに影響文書または文書件数を記録してください。",
        "Review customer-facing export before submission.": "顧客提出前に、顧客向けエクスポート内容を確認してください。",
        "Review the evidence alignment.": "根拠文書との整合を確認してください。",
        "Fix and rerun.": "修正して再検査してください。",
        "Complete human review.": "人間レビューを完了してください。",
        "Add document snapshot IDs, index version, or document version metadata.": (
            "document snapshot ID、index version、または文書バージョン情報を追加してください。"
        ),
        "Attach document corpus evidence before production migration.": (
            "本番移行前に文書コーパスの証跡を添付してください。"
        ),
        "Attach a ChangeEvent before using this packet for release review.": (
            "このpacketをリリースレビューに使う前にChangeEventを添付してください。"
        ),
        "Set a bounded change_type for this review.": (
            "このレビューに限定されたchange_typeを設定してください。"
        ),
        "Record changed assets as bounded metadata.": (
            "変更対象を限定されたmetadataとして記録してください。"
        ),
        "Record the retest reason for this ChangeEvent.": (
            "このChangeEventの再検査理由を記録してください。"
        ),
    }
    return translations.get(raw, raw)


def _customer_sentence_text(text: object) -> str:
    raw = str(text or "").strip()
    translations = {
        "Formal customer submission is not recommended. Use this only as an interim safe draft if the PoC agreement requires shared findings.": (
            "正式な顧客提出は推奨されません。PoC契約上共有が必要な場合のみ、暫定のsafeドラフトとして扱ってください。"
        ),
        "Formal customer submission is not recommended.": (
            "正式な顧客提出は推奨されません。"
        ),
        "Formal customer submission is recommended for the scoped quality review.": (
            "今回の検査範囲では、正式な顧客提出レポートとして利用できます。"
        ),
        "Formal customer submission is conditional on PM approval and documented residual risk.": (
            "正式提出には、PM承認と残留リスクの明記が必要です。"
        ),
        "Document update can change retrieval evidence and answer behavior.": (
            "文書更新により、検索される根拠や回答内容が変わる可能性があります。"
        ),
        "Document update can change retrieval evidence.": (
            "文書更新により、検索される根拠が変わる可能性があります。"
        ),
    }
    return translations.get(raw, raw)


def build_customer_review_markdown(packet: ReviewPacket | dict[str, object]) -> str:
    """Build a safe customer-facing Markdown review from a ReviewPacket."""
    payload = packet.model_dump(mode="json") if isinstance(packet, ReviewPacket) else packet
    decision = payload.get("decision", {}) if isinstance(payload.get("decision"), dict) else {}
    run_summary = (
        payload.get("run_summary", {}) if isinstance(payload.get("run_summary"), dict) else {}
    )
    delivery = (
        payload.get("delivery_review", {})
        if isinstance(payload.get("delivery_review"), dict)
        else {}
    )
    readiness = (
        payload.get("production_readiness", {})
        if isinstance(payload.get("production_readiness"), dict)
        else {}
    )
    change = (
        payload.get("change_summary", {})
        if isinstance(payload.get("change_summary"), dict)
        else {}
    )
    corpus = (
        payload.get("document_corpus", {})
        if isinstance(payload.get("document_corpus"), dict)
        else {}
    )
    shareability = (
        payload.get("customer_shareability", {})
        if isinstance(payload.get("customer_shareability"), dict)
        else {}
    )
    submission = (
        payload.get("customer_submission_readiness", {})
        if isinstance(payload.get("customer_submission_readiness"), dict)
        else {}
    )
    report_sections = (
        payload.get("report_sections", {})
        if isinstance(payload.get("report_sections"), dict)
        else {}
    )
    review_stage = str(payload.get("review_stage") or "unknown")
    title = str(
        report_sections.get("report_title")
        or _customer_report_title(review_stage)
    )
    blocking_items = payload.get("blocking_items", [])
    if not isinstance(blocking_items, list):
        blocking_items = []
    actions = delivery.get("required_actions", [])
    if not isinstance(actions, list):
        actions = []
    decision_status = str(decision.get("customer_status", decision.get("status", "unknown")))
    submission_status = str(submission.get("status", "not_recommended"))
    shareability_status = str(shareability.get("status", delivery.get("customer_submission_status", "needs_review")))
    stage_label = {
        "pre_delivery": "納品前品質診断",
        "post_delivery_change": "納品後変更レビュー",
        "monthly_review": "月次品質レビュー",
    }.get(review_stage, review_stage)
    one_line = "今回の検査結果は本番反映不可です。社内で修正・再検査してください。"
    if decision_status == "Go":
        one_line = "今回の検査範囲では、本番反映および顧客提出に進められる状態です。"
    elif decision_status == "Conditional":
        one_line = "今回の検査結果は条件付きです。残留リスクと承認条件を明記してください。"
    no_go_notice = []
    if decision_status == "No-Go" or submission_status == "not_recommended":
        no_go_notice = [
            "",
            "> このレポートは正式な顧客提出レポートとしては推奨されません。",
            "> 社内で修正・再検査した後、正式提出用レポートを生成してください。",
        ]
    lines = [
        f"# {title}",
        "",
        "## 1行要約",
        one_line,
        *no_go_notice,
        "",
        "## 判定",
        f"- レビュー種別: {stage_label} (`{review_stage}`)",
        f"- 判定: {decision_status}",
        f"- 本番移行準備度: {readiness.get('status', 'unknown')}",
        f"- 情報として共有可能か: {shareability_status}",
        f"- 正式提出として推奨されるか: {submission_status}",
        f"- 推奨コメント: {_customer_sentence_text(submission.get('recommendation', '-') or '-')}",
        "",
        "## 検査範囲",
        f"- Run ID: {run_summary.get('run_id', '')}",
        f"- 総ケース数: {run_summary.get('total_cases', 0)}",
        f"- 合格ケース数: {run_summary.get('passed_cases', 0)}",
        f"- 失敗ケース数: {run_summary.get('failed_cases', 0)}",
        f"- レポートモード: {run_summary.get('report_mode', '')}",
        "",
        "## 変更・文書コーパス",
        f"- 変更種別: {change.get('change_type', 'unknown')}",
        f"- 変更対象数: {change.get('changed_assets_count', 0)}",
        f"- 影響文書数: {change.get('affected_documents_count', 0)}",
        f"- 再検査理由: {_customer_sentence_text(change.get('retest_reason', '-') or '-')}",
        f"- 文書数: {corpus.get('document_count', 0)}",
        f"- 正本種別: {corpus.get('source_of_truth_type', 'unknown')}",
        f"- 文書バージョンあり: {corpus.get('has_document_versions', False)}",
        f"- 古い文書の扱い: {corpus.get('stale_doc_policy', '') or '-'}",
        "",
        "## 未解決ブロッカー",
    ]
    if blocking_items:
        lines.extend(
            (
                f"- {item.get('severity', '-')}: {item.get('issue', '-')} "
                f"({_customer_action_text(item.get('required_action', '-'))})"
            )
            for item in blocking_items
            if isinstance(item, dict)
        )
    else:
        lines.append("- None")
    lines.extend(["", "## 必要な対応"])
    if actions:
        lines.extend(f"- {_customer_action_text(action)}" for action in actions)
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## 残留リスク",
            "- このレビューは設定されたケース、文書、評価条件に基づく範囲限定の確認です。",
            "- PASSやGoであっても、すべてのAI回答の正しさを保証するものではありません。",
            "",
            "## 検査範囲と注意事項",
            "- 顧客共有向けのsafe情報のみで構成しています。",
            "- raw question、answer、evidence text、source path、ownerは含めていません。",
            "- No-Goまたは正式提出非推奨の場合は、社内で修正・再検査してから正式提出してください。",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_evidence_policy(*, packet_mode: str) -> dict[str, object]:
    if packet_mode == "full":
        return {
            "mode": "full",
            "summary": (
                "Full packet may reference customer-controlled evidence and should stay in "
                "local/private/customer-controlled environments."
            ),
            "includes_full_evidence": True,
            "full_evidence_location": "customer-controlled environment",
        }
    return {
        "mode": "safe",
        "summary": (
            "Safe packet excludes raw questions, answers, and evidence text; it keeps "
            "aggregate status, reason codes, and safe references only."
        ),
        "includes_full_evidence": False,
        "full_evidence_location": "",
    }


def _build_production_readiness(
    *,
    decision: GateDecision,
    failures: list[Failure],
    change_summary: dict[str, object],
    review_stage: str,
    document_corpus: dict[str, object],
    evidence_policy: dict[str, object],
) -> dict[str, object]:
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    critical_count = sum(
        1 for failure in failures if failure.customer_severity == "Critical"
    )
    if critical_count:
        blockers.append(
            _readiness_blocker(
                code="critical_failure_remaining",
                label="Critical failure remains",
                reason=f"{critical_count} Critical failure(s) remain unresolved.",
                action="Fix the Critical failure(s) and rerun before production release.",
            )
        )
    if _customer_status(decision) == "No-Go":
        blockers.append(
            _readiness_blocker(
                code="no_go_decision",
                label="Current run is No-Go",
                reason="The quality decision blocks release for this run.",
                action="Resolve blocking issues and rerun the gate.",
            )
        )
    if not bool(document_corpus.get("has_source_of_truth")):
        blockers.append(
            _readiness_blocker(
                code="source_of_truth_missing",
                label="Source of truth is not defined",
                reason="Production readiness requires an approved document source of truth.",
                action="Define the source of truth for the document corpus.",
            )
        )
    stale_required = bool(document_corpus.get("stale_doc_policy_required"))
    if stale_required and not bool(document_corpus.get("has_stale_doc_policy")):
        blockers.append(
            _readiness_blocker(
                code="required_stale_doc_policy_missing",
                label="Required stale document policy is missing",
                reason="The run declares stale document policy as required, but none is set.",
                action="Define the stale document policy before production migration.",
            )
        )

    if not bool(document_corpus.get("has_document_versions")):
        warnings.append(
            _readiness_warning(
                code="document_versions_missing",
                label="Document versions are not available",
                reason="The run cannot show stable document version evidence.",
                action="Add document snapshot IDs, index version, or document version metadata.",
            )
        )
    if not bool(document_corpus.get("has_stale_doc_policy")):
        warnings.append(
            _readiness_warning(
                code="stale_doc_policy_missing",
                label="Stale document policy is not set",
                reason="Old-document handling is not explicit for this review packet.",
                action="Define how stale documents are rejected, flagged, or reviewed.",
            )
        )
    if decision.needs_human_review or any(f.human_review_required for f in failures):
        warnings.append(
            _readiness_warning(
                code="human_review_required",
                label="Human review is required",
                reason="The run includes cases or reliability signals requiring human review.",
                action="Complete human review before treating this run as release evidence.",
            )
        )
    if str(evidence_policy.get("mode") or "").strip() not in {"safe", "full"}:
        warnings.append(
            _readiness_warning(
                code="evidence_policy_unknown",
                label="Evidence policy is unknown",
                reason="The packet does not identify whether it is safe or full evidence.",
                action="Set evidence policy mode before production review.",
            )
        )
    if int(document_corpus.get("document_count") or 0) <= 0:
        warnings.append(
            _readiness_warning(
                code="target_documents_missing",
                label="Target documents are not available",
                reason="No target document evidence was detected for this run.",
                action="Attach document corpus evidence before production migration.",
            )
        )
    if review_stage == "post_delivery_change":
        warnings.extend(_change_event_readiness_warnings(change_summary))

    if blockers:
        status = "not_ready"
    elif warnings:
        status = "conditional"
    else:
        status = "ready"
    required_actions = [item["required_action"] for item in blockers]
    required_actions.extend(item["recommended_action"] for item in warnings)
    return {
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "required_actions": required_actions,
        "readiness_summary": _readiness_summary(status, blockers, warnings),
    }


def _readiness_blocker(*, code: str, label: str, reason: str, action: str) -> dict[str, str]:
    return {
        "code": code,
        "label": label,
        "reason": reason,
        "required_action": action,
        "recommended_action": "",
    }


def _readiness_warning(*, code: str, label: str, reason: str, action: str) -> dict[str, str]:
    return {
        "code": code,
        "label": label,
        "reason": reason,
        "required_action": "",
        "recommended_action": action,
    }


def _change_event_readiness_warnings(change_summary: dict[str, object]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    change_type = str(change_summary.get("change_type") or "unknown")
    has_change = bool(
        change_summary.get("change_id")
        or change_summary.get("change_id_hash")
        or change_summary.get("change_summary")
    )
    if not has_change:
        warnings.append(
            _readiness_warning(
                code="change_event_missing",
                label="Change event is missing",
                reason="The run does not explain what changed before this review.",
                action="Attach a ChangeEvent before using this packet for release review.",
            )
        )
    if change_type == "unknown":
        warnings.append(
            _readiness_warning(
                code="change_type_unknown",
                label="Change type is unknown",
                reason="The change is not classified as document, prompt, model, or retrieval.",
                action="Set a bounded change_type for this review.",
            )
        )
    if int(change_summary.get("changed_assets_count") or 0) <= 0:
        warnings.append(
            _readiness_warning(
                code="changed_assets_missing",
                label="Changed assets are missing",
                reason="The packet does not identify what asset changed.",
                action="Record changed assets as bounded metadata.",
            )
        )
    if (
        change_type == "document_update"
        and int(change_summary.get("affected_documents_count") or 0) <= 0
    ):
        warnings.append(
            _readiness_warning(
                code="affected_documents_missing",
                label="Affected documents are missing",
                reason="Document update reviews should identify affected document count.",
                action="Record affected documents or document count for the ChangeEvent.",
            )
        )
    if not str(change_summary.get("retest_reason") or "").strip():
        warnings.append(
            _readiness_warning(
                code="retest_trigger_unclear",
                label="Retest trigger is unclear",
                reason="The packet does not explain why this change required retesting.",
                action="Record the retest reason for this ChangeEvent.",
            )
        )
    return warnings


def _readiness_summary(
    status: str,
    blockers: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> str:
    if status == "not_ready":
        return (
            f"Not ready for production: {len(blockers)} blocker(s) and "
            f"{len(warnings)} warning(s) need attention."
        )
    if status == "conditional":
        return (
            f"Conditionally ready: no blockers, but {len(warnings)} warning(s) "
            "should be reviewed before production migration."
        )
    if status == "ready":
        return "Ready for production review based on this scoped packet."
    return "Production readiness is unknown because required packet data is missing."


def build_ci_safe_gate_decision_payload(decision: GateDecision) -> dict[str, object]:
    """Return a GateDecision-shaped CI artifact without customer/free-form fields."""
    payload = decision.model_dump(mode="json")
    safe_metrics = {
        str(key): value
        for key, value in payload.get("metrics", {}).items()
        if isinstance(value, int | float)
    }
    payload["metrics"] = safe_metrics
    safe_reason_codes = _ci_safe_reason_codes(payload)
    payload["reasons"] = safe_reason_codes
    payload["reason_codes"] = safe_reason_codes
    payload["provenance"] = _ci_safe_provenance(payload.get("provenance"))
    payload["next_actions"] = [
        {
            "failure_category": _safe_ci_reason_code(item.get("failure_category")),
            "count": int(item.get("count", 0) or 0),
            "action": _safe_ci_reason_code(item.get("failure_category")),
            "owner": "T.B.D.",
            "due": "T.B.D.",
            "affected_case_ids": [],
        }
        for item in payload.get("next_actions", [])
        if isinstance(item, dict)
    ]
    payload["fallback_summary"] = sanitize_payload(payload.get("fallback_summary", {}))
    payload["manual_review_summary"] = _ci_safe_manual_review_summary(
        payload.get("manual_review_summary")
    )
    payload["pack"] = None
    payload["embedding_fallback_reason"] = sanitize_text(payload.get("embedding_fallback_reason"))
    return payload


def _ci_safe_reason_codes(payload: dict[str, object]) -> list[str]:
    """Convert CI decision reasons to bounded reason codes only."""
    codes: list[str] = []
    for item in payload.get("reason_codes", []):
        code = _safe_ci_reason_code(item)
        if code:
            codes.append(code)

    reason_text = " ".join(str(item).lower() for item in payload.get("reasons", []))
    if "s1 pass rate" in reason_text or ("s1" in reason_text and "case:" in reason_text):
        codes.append("s1_case_failed")
    if "overall pass rate" in reason_text:
        codes.append("overall_threshold_not_met")
    if "expected evidence" in reason_text or "evidence recall" in reason_text:
        codes.append("expected_evidence_recall_below_threshold")
    if "judge fallback" in reason_text:
        codes.append("judge_fallback_used")
    if "human review" in reason_text:
        codes.append("needs_human_review")
    if "embedding fallback" in reason_text:
        codes.append("embedding_fallback_used")

    if str(payload.get("status") or "").lower() == "fail" and not any(
        code != CI_UNKNOWN_REASON_CODE for code in codes
    ):
        codes.append("threshold_not_met")

    deduped: list[str] = []
    seen: set[str] = set()
    for code in codes:
        if code not in seen:
            seen.add(code)
            deduped.append(code)
    return deduped[:10]


def _normalize_reason_code(value: object) -> str:
    code = sanitize_text(str(value or "")).strip().lower().replace("-", "_").replace(" ", "_")
    if not code:
        return ""
    if all(ch.isalnum() or ch == "_" for ch in code):
        return code[:80]
    return ""


def _safe_ci_reason_code(value: object) -> str:
    code = _normalize_reason_code(value)
    if not code:
        return ""
    if code in CI_SAFE_REASON_CODES:
        return code
    if code in CI_REASON_ALIASES:
        return CI_REASON_ALIASES[code]
    return CI_UNKNOWN_REASON_CODE


def build_ci_safe_history_summary_payload(payload: dict[str, object]) -> dict[str, object]:
    """Return aggregate-only history summary for GitHub-hosted CI artifacts."""
    stale = payload.get("stale_case_review")
    stale_summary: dict[str, object] | None = None
    if isinstance(stale, dict):
        stale_summary = {
            "stale_after_days": stale.get("stale_after_days"),
            "fresh_case_review_rate": stale.get("fresh_case_review_rate"),
            "fresh_case_count": stale.get("fresh_case_count"),
            "total_cases": stale.get("total_cases"),
            "stale_cases_count": stale.get("stale_cases_count", 0),
        }

    comparison = payload.get("comparison")
    safe_comparison = None
    if isinstance(comparison, dict):
        safe_comparison = {
            "current_run_id": sanitize_text(str(comparison.get("current_run_id", ""))),
            "previous_run_id": sanitize_text(str(comparison.get("previous_run_id", ""))),
            "current_status": sanitize_text(str(comparison.get("current_status", ""))),
            "previous_status": sanitize_text(str(comparison.get("previous_status", ""))),
            "metric_deltas": sanitize_payload(comparison.get("metric_deltas", [])),
            "action_deltas": _ci_safe_action_deltas(comparison.get("action_deltas", [])),
        }

    reliability = payload.get("reliability")
    safe_reliability = None
    if isinstance(reliability, dict):
        safe_reliability = {
            key: sanitize_payload(value)
            for key, value in reliability.items()
            if key != "fallback_summary"
        }

    status_mix = payload.get("status_mix", {})
    entries = payload.get("entries", 0)
    summary_lines = [
        f"- Entries: {entries}",
        f"- Status mix: {status_mix}",
    ]
    if payload.get("execution_mode"):
        summary_lines.append(
            f"- Execution mode: {sanitize_text(str(payload.get('execution_mode')))}"
        )

    return {
        "entries": entries,
        "status_mix": status_mix,
        "execution_mode": sanitize_text(str(payload.get("execution_mode") or "")) or None,
        "week_start": payload.get("week_start"),
        "compare_offset": payload.get("compare_offset"),
        "trend_window": payload.get("trend_window"),
        "summary_lines": summary_lines,
        "trend": sanitize_payload(payload.get("trend")),
        "comparison": safe_comparison,
        "failure_action_coverage": _ci_safe_failure_action_coverage(
            payload.get("failure_action_coverage")
        ),
        "uncovered_categories": [],
        "stale_case_review": stale_summary,
        "reliability": safe_reliability,
        "review_steward": None,
    }


def _ci_safe_provenance(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    allowed_suffixes = ("_hash", "_version")
    allowed_keys = {
        "execution_mode",
        "quality_pack_version",
        "case_set_version",
        "index_version",
    }
    return {
        str(key): sanitize_payload(item)
        for key, item in value.items()
        if str(key) in allowed_keys or str(key).endswith(allowed_suffixes)
    }


def _ci_safe_manual_review_summary(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {
        key: value.get(key, 0)
        for key in (
            "total_reviews",
            "approved",
            "rejected",
            "needs_followup",
            "waived_with_risk",
        )
        if key in value
    }


def _ci_safe_failure_action_coverage(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {
        "total_categories": value.get("total_categories"),
        "covered_categories": value.get("covered_categories"),
        "coverage_rate": value.get("coverage_rate"),
        "window_size": value.get("window_size"),
    }


def _ci_safe_action_deltas(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "failure_category": _safe_ci_reason_code(item.get("failure_category")),
                "previous_count": int(item.get("previous_count", 0) or 0),
                "current_count": int(item.get("current_count", 0) or 0),
                "delta": int(item.get("delta", 0) or 0),
            }
        )
    return rows


def _overall_decision_from_gate_decision(decision: GateDecision) -> str:
    if decision.policy_status == "block":
        return "ng"
    if decision.policy_status in {"warn", "needs_human_review"} or decision.needs_human_review:
        return "needs_confirmation"
    if decision.status == "fail":
        return "needs_confirmation"
    return "ok"


def _build_bundle_summary_from_decision(decision: GateDecision) -> dict[str, object]:
    return {
        "headline": "Gate report bundle generated.",
        "overall_pass_rate": decision.metrics.get("overall_pass_rate"),
        "s1_pass_rate": decision.metrics.get("s1_pass_rate"),
        "needs_human_review": decision.needs_human_review,
        "judge_fallback_count": decision.judge_fallback_count,
    }


def _resolve_client_name(decision: GateDecision) -> str | None:
    pack = decision.pack
    if pack is None:
        return None
    extras = getattr(pack, "model_extra", None) or {}
    for value in (
        extras.get("client_name"),
        extras.get("tenant_name"),
        getattr(pack, "tenant_name", None),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _resolve_app_name(decision: GateDecision) -> str | None:
    pack = decision.pack
    if pack is None:
        return None
    extras = getattr(pack, "model_extra", None) or {}
    for value in (
        extras.get("app_name"),
        getattr(pack, "pack_name", None),
        getattr(pack, "name", None),
        getattr(pack, "pack_id", None),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_change_event(decision: GateDecision) -> object | None:
    pack = decision.pack
    if pack is None:
        return None
    extras = getattr(pack, "model_extra", None) or {}
    return extras.get("change_event")


def safe_relative_artifact_path(path: str | Path, base_dir: str | Path) -> str:
    """Return a stable relative artifact reference without exposing host paths."""
    artifact_path = Path(path)
    artifact_base_dir = Path(base_dir)
    try:
        relative = Path(os.path.relpath(artifact_path, start=artifact_base_dir))
    except ValueError:
        relative = Path(artifact_path.name)
    if any(part in {".tmp", "tmp"} for part in relative.parts):
        relative = Path(artifact_path.name)
    return relative.as_posix()


def _append_jsonl_output(path: str | Path, model: GateDecision) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(model.model_dump_json() + "\n")
    return output_path


def _write_json_model_output(path: str | Path, model: GateDecision) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def _write_json_data_output(path: str | Path, payload: object) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def _write_text_output(path: str | Path, content: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path
