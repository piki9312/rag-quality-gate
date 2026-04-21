"""Gate report adapters for emitting reusable output artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from rqg.domain import GateDecision

GATE_REPORT_BUNDLE_TYPE = "rqg.gate_report_bundle"
GATE_REPORT_BUNDLE_SCHEMA_VERSION = "1.0"
GATE_REPORT_BUNDLE_CONTRACT_NAME = "rqg.gate_report_bundle"
GATE_REPORT_BUNDLE_STABLE_FIELDS = (
    "schema_version",
    "bundle_type",
    "contract",
    "generated_at",
    "run",
    "decision",
    "history_summary",
    "report_markdown",
    "artifact_paths",
)


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
    generated_at = _format_datetime_iso(artifacts.decision.created_at)
    return {
        "schema_version": GATE_REPORT_BUNDLE_SCHEMA_VERSION,
        "bundle_type": GATE_REPORT_BUNDLE_TYPE,
        "contract": {
            "name": GATE_REPORT_BUNDLE_CONTRACT_NAME,
            "version": GATE_REPORT_BUNDLE_SCHEMA_VERSION,
            "stable_fields": list(GATE_REPORT_BUNDLE_STABLE_FIELDS),
            "compatibility": (
                "minor changes are additive; existing stable fields remain backward "
                "compatible within the same major version"
            ),
        },
        "generated_at": generated_at,
        "run": {
            "run_id": artifacts.decision.run_id,
            "status": artifacts.decision.status,
            "created_at": generated_at,
        },
        "decision": artifacts.decision.model_dump(mode="json"),
        "history_summary": artifacts.history_summary,
        "report_markdown": artifacts.markdown,
        "artifact_paths": {
            "report_path": artifacts.report_path.as_posix(),
            "decision_path": artifacts.decision_path.as_posix(),
            "history_summary_path": artifacts.history_summary_path.as_posix(),
            "history_path": artifacts.history_path.as_posix(),
            "bundle_path": artifacts.bundle_path.as_posix(),
        },
    }


def _append_jsonl_output(path: str | Path, model: GateDecision) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(model.model_dump_json() + "\n")
    return output_path


def _format_datetime_iso(value: datetime) -> str:
    if value.tzinfo is None:
        return value.isoformat()
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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
