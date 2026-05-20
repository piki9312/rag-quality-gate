"""Allowlist-based field exposure policy for report artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .report_mode_policy import normalize_report_mode_value


class ArtifactType(str, Enum):
    GATE_REPORT_JSON = "gate_report_json"
    CUSTOMER_SUMMARY = "customer_summary"
    CI_CASE_ROW = "ci_case_row"


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


def resolve_artifact_exposure(
    artifact_type: ArtifactType | str,
    report_mode: object,
) -> ArtifactExposurePolicy:
    """Resolve the allowlist policy for one artifact/report mode pair."""
    resolved_artifact_type = ArtifactType(artifact_type)
    normalized_report_mode = normalize_report_mode_value(report_mode)

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
