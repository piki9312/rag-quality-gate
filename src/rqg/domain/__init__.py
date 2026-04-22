"""Domain models for Phase 1 quality gate scaffolding."""

from .connection_validation import ConnectionValidationErrorType, ConnectionValidationResult
from .document_snapshot import DocumentSnapshot
from .eval_case import EvalCase
from .gate_decision import GateDecision, GateNextAction, GatePackMetadata
from .impact_report import ImpactDetail, ImpactReport

__all__ = [
    "ConnectionValidationResult",
    "ConnectionValidationErrorType",
    "DocumentSnapshot",
    "EvalCase",
    "GateDecision",
    "GateNextAction",
    "GatePackMetadata",
    "ImpactDetail",
    "ImpactReport",
]
