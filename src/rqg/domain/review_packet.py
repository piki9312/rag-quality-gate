"""Review packet domain models for customer-facing release review."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CustomerSeverity = Literal["Critical", "High", "Medium", "Low"]
ReviewPacketMode = Literal["safe", "full"]
ProductionReadinessStatus = Literal["ready", "conditional", "not_ready", "unknown"]
ReviewStage = Literal["pre_delivery", "post_delivery_change", "monthly_review", "unknown"]
DeliveryReviewStatus = Literal[
    "deliverable",
    "needs_fix",
    "needs_approval",
    "not_deliverable",
    "unknown",
]
CustomerSubmissionStatus = Literal["safe_to_share", "needs_review", "not_safe"]
CustomerShareabilityStatus = Literal["shareable", "needs_review", "not_shareable"]
CustomerSubmissionReadinessStatus = Literal["recommended", "conditional", "not_recommended"]
ReleaseDecisionValue = Literal["approved", "rejected", "conditional", "needs_review"]


class BlockingReason(BaseModel):
    """A bounded reason explaining why a run blocks or needs review."""

    reason_code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    severity: CustomerSeverity
    affected_count: int = Field(default=0, ge=0)
    why_it_blocks: str = ""

    model_config = ConfigDict(extra="forbid")


class DecisionExplanation(BaseModel):
    """Plain-language decision payload for Run Detail decision cards."""

    headline: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    plain_language_reason: str = Field(min_length=1)
    blocking_reasons: list[BlockingReason] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class Failure(BaseModel):
    """Failure summary used by ReviewPacket and future Failure Detail screens."""

    failure_id: str = Field(min_length=1)
    case_id: str = ""
    case_id_hash: str = Field(min_length=1)
    customer_severity: CustomerSeverity
    internal_severity: str = ""
    failure_category: str = ""
    failure_pattern: str = ""
    business_category: str = ""
    go_no_go_impact: str = ""
    human_review_required: bool = False
    question_summary: str = ""
    expected_summary: str = ""
    actual_summary: str = ""
    evidence_status: str = ""
    safe_reason_code: str = ""
    next_action: str = ""
    suggested_fix: str = ""
    full_detail_ref: str = ""

    model_config = ConfigDict(extra="forbid")


class RunSummary(BaseModel):
    run_id: str
    created_at: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    pass_rate: float = 0.0
    report_mode: str = "full"

    model_config = ConfigDict(extra="forbid")


class ReviewDecision(BaseModel):
    status: str
    policy_status: str
    customer_status: str
    needs_human_review: bool = False

    model_config = ConfigDict(extra="forbid")


class ReviewScope(BaseModel):
    target_name: str = ""
    target_type: str = ""
    target_documents: list[str] = Field(default_factory=list)
    document_versions: list[str] = Field(default_factory=list)
    change_event: object | None = None

    model_config = ConfigDict(extra="forbid")


class DocumentMetadata(BaseModel):
    """Full-mode document metadata for corpus evidence review."""

    document_id: str = ""
    title: str = ""
    version: str = ""
    content_hash: str = ""
    snapshot_id: str = ""
    last_updated_at: str = ""
    owner: str = ""
    source_path: str = ""

    model_config = ConfigDict(extra="forbid")


class DocumentCorpus(BaseModel):
    """Document corpus evidence scope for RAG release review."""

    document_count: int = Field(default=0, ge=0)
    source_of_truth_type: str = "unknown"
    stale_doc_policy: str = ""
    stale_doc_policy_required: bool = False
    version_hashes: list[str] = Field(default_factory=list)
    has_document_versions: bool = False
    has_source_of_truth: bool = False
    has_stale_doc_policy: bool = False
    target_documents: list[DocumentMetadata] = Field(default_factory=list)
    source_of_truth: str = ""
    affected_business_categories: list[str] = Field(default_factory=list)
    affected_cases: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ChangeSummary(BaseModel):
    """Bounded change event summary for release review."""

    change_type: str = "unknown"
    change_id: str = ""
    change_id_hash: str = ""
    changed_assets_count: int = Field(default=0, ge=0)
    affected_documents_count: int = Field(default=0, ge=0)
    affected_business_categories: list[str] = Field(default_factory=list)
    target_release: str = ""
    change_summary: str = ""
    retest_reason: str = ""
    changed_assets: list[str] = Field(default_factory=list)
    affected_documents: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class SeveritySummary(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0

    model_config = ConfigDict(extra="forbid")


class RiskBreakdown(BaseModel):
    major_misguidance: int = 0
    evidence_mismatch: int = 0
    stale_reference: int = 0
    business_rule_violation: int = 0
    human_review_required: int = 0

    model_config = ConfigDict(extra="forbid")


class ReportSections(BaseModel):
    report_title: str = ""
    executive_summary: str = ""
    decision: str = ""
    change_summary: str = ""
    scope: str = ""
    production_readiness: str = ""
    delivery_review: str = ""
    customer_submission: str = ""
    major_risks: str = ""
    blocking_issues: str = ""
    required_actions: str = ""
    residual_risks: str = ""
    disclaimer: str = ""

    model_config = ConfigDict(extra="forbid")


class EvidencePolicySummary(BaseModel):
    mode: ReviewPacketMode = "safe"
    summary: str
    includes_full_evidence: bool = False
    full_evidence_location: str = ""

    model_config = ConfigDict(extra="forbid")


class ProductionReadinessIssue(BaseModel):
    """Bounded production readiness blocker or warning."""

    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    reason: str = ""
    required_action: str = ""
    recommended_action: str = ""

    model_config = ConfigDict(extra="forbid")


class ProductionReadiness(BaseModel):
    """PoC-to-production readiness summary for ReviewPacket consumers."""

    status: ProductionReadinessStatus = "unknown"
    blockers: list[ProductionReadinessIssue] = Field(default_factory=list)
    warnings: list[ProductionReadinessIssue] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    readiness_summary: str = ""

    model_config = ConfigDict(extra="forbid")


class BlockingItem(BaseModel):
    """Unresolved S1/S2 item used by PM delivery review."""

    item_id: str = Field(min_length=1)
    severity: str = ""
    issue: str = ""
    category: str = ""
    blocks_delivery: bool = False
    required_action: str = ""
    owner: str = ""
    due_date: str = ""
    status: str = "open"

    model_config = ConfigDict(extra="forbid")


class CustomerShareability(BaseModel):
    """Safe export readiness for customer-facing review artifacts."""

    status: CustomerShareabilityStatus = "needs_review"
    reasons: list[str] = Field(default_factory=list)
    forbidden_fields_detected: list[str] = Field(default_factory=list)
    safe_mode_required: bool = True

    model_config = ConfigDict(extra="forbid")


class CustomerSubmissionReadiness(BaseModel):
    """Whether the safe artifact is appropriate as a formal customer submission."""

    status: CustomerSubmissionReadinessStatus = "not_recommended"
    reasons: list[str] = Field(default_factory=list)
    recommendation: str = ""

    model_config = ConfigDict(extra="forbid")


class DeliveryReview(BaseModel):
    """PM-facing delivery decision summary."""

    status: DeliveryReviewStatus = "unknown"
    summary: str = ""
    unresolved_s1_count: int = Field(default=0, ge=0)
    unresolved_s2_count: int = Field(default=0, ge=0)
    blockers: list[BlockingItem] = Field(default_factory=list)
    customer_submission_status: CustomerSubmissionStatus = "needs_review"
    required_actions: list[str] = Field(default_factory=list)
    reviewer_notes_placeholder: str = ""

    model_config = ConfigDict(extra="forbid")


class ReleaseDecision(BaseModel):
    """Minimal human decision record for later approval workflows."""

    decision: ReleaseDecisionValue = "needs_review"
    decided_by: str = ""
    decided_at: str = ""
    reviewer_role: str = ""
    accepted_risks: list[str] = Field(default_factory=list)
    unresolved_blockers: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str = ""

    model_config = ConfigDict(extra="forbid")


class ReviewPacket(BaseModel):
    """Intermediate payload for Run Detail, Failure Detail, and Report Preview."""

    schema_version: str = "1.0"
    packet_mode: ReviewPacketMode = "safe"
    review_stage: ReviewStage = "unknown"
    run_summary: RunSummary
    decision: ReviewDecision
    decision_explanation: DecisionExplanation
    scope: ReviewScope = Field(default_factory=ReviewScope)
    change_summary: ChangeSummary = Field(default_factory=ChangeSummary)
    document_corpus: DocumentCorpus = Field(default_factory=DocumentCorpus)
    severity_summary: SeveritySummary = Field(default_factory=SeveritySummary)
    risk_breakdown: RiskBreakdown = Field(default_factory=RiskBreakdown)
    major_failures: list[Failure] = Field(default_factory=list)
    report_sections: ReportSections = Field(default_factory=ReportSections)
    evidence_policy: EvidencePolicySummary
    production_readiness: ProductionReadiness = Field(default_factory=ProductionReadiness)
    delivery_review: DeliveryReview = Field(default_factory=DeliveryReview)
    blocking_items: list[BlockingItem] = Field(default_factory=list)
    customer_shareability: CustomerShareability = Field(default_factory=CustomerShareability)
    customer_submission_readiness: CustomerSubmissionReadiness = Field(
        default_factory=CustomerSubmissionReadiness
    )
    release_decision: ReleaseDecision = Field(default_factory=ReleaseDecision)

    model_config = ConfigDict(extra="forbid")


def stable_case_id_hash(case_id: object) -> str:
    """Return a short stable case identifier for safe payloads."""
    return hashlib.sha256(str(case_id or "").encode("utf-8")).hexdigest()[:16]


def map_customer_severity(
    *,
    internal_severity: object,
    failure_category: object = "",
    failure_type: object = "",
    business_category: object = "",
    required_action: object = "",
    human_review_required: bool = False,
) -> CustomerSeverity:
    """Map internal S1/S2 and business risk hints to customer-facing severity."""
    severity = str(internal_severity or "").strip().upper()
    text = " ".join(
        str(value or "").strip().lower()
        for value in (failure_category, failure_type, business_category, required_action)
    )

    business_critical_terms = {
        "billing",
        "cancel",
        "cancellation",
        "contract",
        "payment",
        "pricing",
        "refund",
        "terms",
    }
    evidence_terms = {
        "bad_reference",
        "evidence",
        "evidence_mismatch",
        "missing_evidence",
        "retrieval",
        "retrieval_miss",
        "source_mismatch",
    }
    light_terms = {"style", "wording", "format", "typo", "ambiguous", "minor"}

    if severity == "S1":
        if any(term in text for term in business_critical_terms):
            return "Critical"
        if any(term in text for term in evidence_terms):
            return "High"
        return "High"

    if severity == "S2":
        if human_review_required and "human_review" in text:
            return "Low"
        if any(term in text for term in light_terms):
            return "Low"
        return "Medium"

    return "Low"
