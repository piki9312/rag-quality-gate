"""Allowlist-based field exposure policy for report artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .report_mode_policy import normalize_report_mode_value


class ArtifactType(str, Enum):
    GATE_REPORT_JSON = "gate_report_json"
    CUSTOMER_SUMMARY = "customer_summary"
    CI_CASE_ROW = "ci_case_row"
    NOTIFICATION_PAYLOAD = "notification_payload"
    HISTORY_SUMMARY = "history_summary"
    GATE_DECISION_HISTORY = "gate_decision_history"
    GATE_DECISION_HISTORY_SAFE = "gate_decision_history_safe"


class FieldExposure(str, Enum):
    ALLOWED = "allowed"
    HASHED_ONLY = "hashed_only"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True, slots=True)
class ArtifactExposurePolicy:
    artifact_type: ArtifactType
    report_mode: str
    allowed_fields: frozenset[str]
    hashed_only_fields: frozenset[str]
    forbidden_fields: frozenset[str]

    def exposure_for(self, field_name: str) -> FieldExposure:
        """Return the exposure category for a field, defaulting to deny."""
        if field_name in self.allowed_fields:
            return FieldExposure.ALLOWED
        if field_name in self.hashed_only_fields:
            return FieldExposure.HASHED_ONLY
        return FieldExposure.FORBIDDEN

    def allows(self, field_name: str) -> bool:
        return self.exposure_for(field_name) == FieldExposure.ALLOWED

    def hashes_only(self, field_name: str) -> bool:
        return self.exposure_for(field_name) == FieldExposure.HASHED_ONLY


_FULL_ALLOWED = frozenset(
    {
        "aggregate_metrics",
        "ai_answer",
        "answer_hash",
        "case_id",
        "category",
        "decision",
        "expected_answer",
        "expected_evidence",
        "fail_reason",
        "failure_type_code",
        "judge_fallback_reason",
        "judge_fallback_used",
        "judge_reliability",
        "name",
        "needs_human_review",
        "next_actions",
        "pass_fail",
        "question",
        "retrieved_evidence",
        "risk_domain",
        "severity",
        "source_doc",
        "target_docs",
    }
)

_REDACTED_ALLOWED = frozenset(
    {
        "aggregate_metrics",
        "answer_hash",
        "category",
        "decision",
        "failure_type_code",
        "judge_fallback_used",
        "judge_reliability",
        "needs_human_review",
        "next_actions",
        "pass_fail",
        "risk_domain",
        "safe_reason",
        "severity",
    }
)

_CI_ALLOWED = frozenset(
    {
        "aggregate_metrics",
        "decision",
        "failure_type_code",
        "judge_fallback_used",
        "latency_ms",
        "cost_usd",
        "evidence_recall",
        "faithfulness_score",
        "judge_relevance",
        "needs_human_review",
        "pass_fail",
        "safe_reason_code",
        "severity",
    }
)

_FULL_FORBIDDEN = frozenset({"api_key", "api_keys", "secret", "secrets", "token", "tokens"})

_REDACTED_FORBIDDEN = frozenset(
    {
        "ai_answer",
        "answer",
        "expected_answer",
        "expected_evidence",
        "fail_reason",
        "internal_notes",
        "notes",
        "question",
        "raw_answer",
        "raw_fail_reason",
        "retrieved_evidence",
        "source_doc",
    }
)

_CI_FORBIDDEN = frozenset(
    {
        "ai_answer",
        "answer",
        "case_id",
        "change_event",
        "customer_authored_identifiers",
        "expected_answer",
        "expected_evidence",
        "fail_reason",
        "question",
        "raw_fail_reason",
        "source_doc",
        "target_docs",
    }
)

_NOTIFICATION_ALLOWED = frozenset(
    {
        "case_id_hash",
        "created_at",
        "decision_path",
        "event",
        "execution_mode",
        "failed_cases",
        "failure_category",
        "failure_type_code",
        "gate_status",
        "needs_human_review",
        "overall_pass_rate",
        "policy_status",
        "reason_code",
        "reason_codes",
        "report_mode",
        "report_path",
        "run_id",
        "s1_failed_count",
        "s1_pass_rate",
        "safe_reason_codes",
        "status",
        "summary",
        "text",
        "total_cases",
    }
)

_NOTIFICATION_FORBIDDEN = frozenset(
    {
        "ai_answer",
        "answer",
        "api_key",
        "api_keys",
        "case_id",
        "change_event",
        "customer_authored_identifiers",
        "endpoint",
        "endpoint_url",
        "expected_answer",
        "expected_evidence",
        "fail_reason",
        "failure_reason",
        "internal_notes",
        "notes",
        "question",
        "rag_endpoint",
        "raw_answer",
        "raw_case_id",
        "raw_change_event",
        "raw_fail_reason",
        "retrieved_evidence",
        "secret",
        "secrets",
        "source_doc",
        "target_docs",
        "token",
        "tokens",
    }
)

_HISTORY_ALLOWED = frozenset(
    {
        "action_deltas",
        "age_days",
        "aggregate_counts",
        "adapter_config_hash",
        "baseline_runs",
        "case_id_hash",
        "case_id_hashes",
        "case_set_version",
        "compare_offset",
        "comparison",
        "covered",
        "covered_categories",
        "coverage_rate",
        "created_at",
        "current",
        "current_count",
        "current_run_id",
        "current_runs",
        "current_status",
        "delta",
        "embedding_fallback_count",
        "embedding_fallback_used",
        "entries",
        "execution_mode",
        "failed_cases",
        "failure_action_coverage",
        "failure_category",
        "failure_type_code",
        "fresh_case_count",
        "fresh_case_review_rate",
        "gate_status",
        "index_version",
        "judge_failure_types",
        "judge_fallback_count",
        "judge_fallback_used",
        "judge_reliability",
        "key",
        "label",
        "last_seen_run_id",
        "latest_run_id",
        "latest_status",
        "metric_deltas",
        "model_name",
        "needs_human_review",
        "new_reason_codes",
        "overall_pass_rate",
        "pass",
        "policy_status",
        "previous",
        "previous_count",
        "previous_run_id",
        "previous_status",
        "prompt_hash",
        "provenance",
        "quality_pack_version",
        "reason_code",
        "reason_codes",
        "reliability",
        "report_mode",
        "retrieval_reliability",
        "retrieval_config_hash",
        "resolved_reason_codes",
        "review_steward",
        "run_id",
        "s1_failed_count",
        "s1_pass_rate",
        "safe_reason_codes",
        "stale_after_days",
        "stale_case_review",
        "stale_cases",
        "stale_cases_count",
        "status_mix",
        "status_sequence",
        "streak_count",
        "summary_lines",
        "total_cases",
        "total_categories",
        "total_count",
        "trend",
        "trend_metrics",
        "trend_window",
        "uncovered_categories",
        "unit",
        "warn",
        "week_start",
        "window_size",
        "fail",
    }
)

_HISTORY_FORBIDDEN = frozenset(
    {
        "ai_answer",
        "answer",
        "api_key",
        "api_keys",
        "case_id",
        "change_event",
        "change_event_text",
        "customer_name",
        "endpoint",
        "endpoint_url",
        "expected_answer",
        "expected_evidence",
        "fail_reason",
        "failure_reason",
        "internal_notes",
        "name",
        "notes",
        "owner",
        "question",
        "rag_endpoint",
        "raw_answer",
        "raw_case_id",
        "raw_change_event",
        "raw_fail_reason",
        "reference_value",
        "retrieved_evidence",
        "secret",
        "secrets",
        "source_doc",
        "summary",
        "target_docs",
        "token",
        "tokens",
    }
)

_GATE_DECISION_HISTORY_SAFE_ALLOWED = _HISTORY_ALLOWED - frozenset({"review_steward"})

_GATE_DECISION_HISTORY_SAFE_FORBIDDEN = _HISTORY_FORBIDDEN | frozenset(
    {"review_owner", "review_steward", "steward"}
)


def resolve_artifact_exposure(
    artifact_type: ArtifactType | str,
    report_mode: object,
) -> ArtifactExposurePolicy:
    """Resolve the allowlist policy for one artifact/report mode pair."""
    resolved_artifact_type = ArtifactType(artifact_type)
    normalized_report_mode = normalize_report_mode_value(report_mode)

    if resolved_artifact_type == ArtifactType.NOTIFICATION_PAYLOAD:
        return ArtifactExposurePolicy(
            artifact_type=resolved_artifact_type,
            report_mode=normalized_report_mode,
            allowed_fields=_NOTIFICATION_ALLOWED,
            hashed_only_fields=frozenset({"case_id"}),
            forbidden_fields=_NOTIFICATION_FORBIDDEN,
        )
    if resolved_artifact_type == ArtifactType.GATE_DECISION_HISTORY_SAFE:
        return ArtifactExposurePolicy(
            artifact_type=resolved_artifact_type,
            report_mode=normalized_report_mode,
            allowed_fields=_GATE_DECISION_HISTORY_SAFE_ALLOWED,
            hashed_only_fields=frozenset(
                {"case_id", "change_event_id", "source_doc", "target_docs"}
            ),
            forbidden_fields=_GATE_DECISION_HISTORY_SAFE_FORBIDDEN,
        )
    if resolved_artifact_type in {
        ArtifactType.HISTORY_SUMMARY,
        ArtifactType.GATE_DECISION_HISTORY,
    }:
        return ArtifactExposurePolicy(
            artifact_type=resolved_artifact_type,
            report_mode=normalized_report_mode,
            allowed_fields=_HISTORY_ALLOWED,
            hashed_only_fields=frozenset(
                {"case_id", "change_event_id", "source_doc", "target_docs"}
            ),
            forbidden_fields=_HISTORY_FORBIDDEN,
        )

    if normalized_report_mode == "full":
        return ArtifactExposurePolicy(
            artifact_type=resolved_artifact_type,
            report_mode=normalized_report_mode,
            allowed_fields=_FULL_ALLOWED,
            hashed_only_fields=frozenset(),
            forbidden_fields=_FULL_FORBIDDEN,
        )
    if normalized_report_mode == "redacted":
        return ArtifactExposurePolicy(
            artifact_type=resolved_artifact_type,
            report_mode=normalized_report_mode,
            allowed_fields=_REDACTED_ALLOWED,
            hashed_only_fields=frozenset({"case_id", "target_docs"}),
            forbidden_fields=_REDACTED_FORBIDDEN,
        )
    return ArtifactExposurePolicy(
        artifact_type=resolved_artifact_type,
        report_mode=normalized_report_mode,
        allowed_fields=_CI_ALLOWED,
        hashed_only_fields=frozenset({"case_id"}),
        forbidden_fields=_CI_FORBIDDEN,
    )
