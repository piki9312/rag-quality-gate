"""Gate report adapters for emitting reusable output artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from rqg.domain import GateDecision

GATE_REPORT_SCHEMA_VERSION = "1.0"


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
    check_result: Any | None = None


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
        return _write_json_model_output(self.path, artifacts.decision)


class HistorySummaryJsonReportAdapter:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def emit(self, artifacts: GateReportArtifacts) -> Path:
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
    decision_payload = artifacts.decision.model_dump(mode="json")
    payload = {
        "schema_version": GATE_REPORT_SCHEMA_VERSION,
        "decision": decision_payload,
        "history_summary": artifacts.history_summary,
        "report_markdown": artifacts.markdown,
        "artifact_paths": {
            "report_path": str(artifacts.report_path),
            "decision_path": str(artifacts.decision_path),
            "history_summary_path": str(artifacts.history_summary_path),
            "history_path": str(artifacts.history_path),
            "bundle_path": str(artifacts.bundle_path),
        },
    }

    cases: list[dict[str, object]] = []
    target_docs: list[str] = []
    summary = _build_bundle_summary_from_decision(artifacts.decision)
    overall_decision = _overall_decision_from_gate_decision(artifacts.decision)

    if artifacts.check_result is not None:
        from rqg.quality.check import (
            build_case_report_rows,
            build_customer_report_summary,
            collect_target_docs,
            map_overall_decision,
        )

        cases = build_case_report_rows(artifacts.check_result)
        target_docs = collect_target_docs(artifacts.check_result)
        summary = build_customer_report_summary(artifacts.check_result)
        overall_decision = map_overall_decision(artifacts.check_result)

    payload.update(
        {
            "report_version": GATE_REPORT_SCHEMA_VERSION,
            "executed_at": decision_payload["created_at"],
            "client_name": _resolve_client_name(artifacts.decision),
            "app_name": _resolve_app_name(artifacts.decision),
            "target_docs": target_docs,
            "change_event": _extract_change_event(artifacts.decision),
            "summary": summary,
            "overall_decision": overall_decision,
            "cases": cases,
        }
    )
    return payload


def _overall_decision_from_gate_decision(decision: GateDecision) -> str:
    if decision.policy_status == "block" or decision.status == "fail":
        return "ng"
    if decision.policy_status in {"warn", "needs_human_review"} or decision.needs_human_review:
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
