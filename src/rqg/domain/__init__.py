"""Domain models for Phase 1 quality gate scaffolding."""

from .document_snapshot import DocumentSnapshot
from .eval_case import EvalCase
from .gate_decision import GateDecision, GateNextAction
from .impact_report import ImpactDetail, ImpactReport

__all__ = [
    "DocumentSnapshot",
    "EvalCase",
    "GateDecision",
    "GateNextAction",
    "ImpactDetail",
    "ImpactReport",
]
