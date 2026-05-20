"""Domain models for Phase 1 quality gate scaffolding."""

from .connection_validation import ConnectionValidationErrorType, ConnectionValidationResult
from .change_event import ChangedAsset, ChangeEvent
from .document_snapshot import DocumentSnapshot
from .eval_case import EvalCase
from .gate_decision import GateApprovalInfo, GateDecision, GateNextAction, GatePackMetadata
from .impact_report import ImpactDetail, ImpactReport
from .review_packet import (
    BlockingReason,
    BlockingItem,
    ChangeSummary,
    CustomerSubmissionReadiness,
    CustomerShareability,
    DecisionExplanation,
    DeliveryReview,
    DocumentCorpus,
    DocumentMetadata,
    Failure,
    ProductionReadiness,
    ProductionReadinessIssue,
    ReleaseDecision,
    ReviewPacket,
    map_customer_severity,
)

__all__ = [
    "ConnectionValidationResult",
    "ConnectionValidationErrorType",
    "ChangeEvent",
    "ChangedAsset",
    "DocumentSnapshot",
    "EvalCase",
    "GateDecision",
    "GateNextAction",
    "GatePackMetadata",
    "GateApprovalInfo",
    "ImpactDetail",
    "ImpactReport",
    "ReviewPacket",
    "Failure",
    "ChangeSummary",
    "CustomerSubmissionReadiness",
    "CustomerShareability",
    "DecisionExplanation",
    "DeliveryReview",
    "BlockingReason",
    "BlockingItem",
    "DocumentCorpus",
    "DocumentMetadata",
    "ProductionReadiness",
    "ProductionReadinessIssue",
    "ReleaseDecision",
    "map_customer_severity",
]
