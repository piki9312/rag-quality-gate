"""Gate report adapters for emitting reusable output artifacts."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from rqg.domain import GateDecision
from rqg.security import sanitize_payload, sanitize_text

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
            build_customer_report_summary,
            collect_target_docs_if_report_mode_allows,
            map_overall_decision,
            normalize_report_mode,
        )

        normalized_report_mode = normalize_report_mode(report_mode)
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
            "app_name": None if report_mode == "ci" else _resolve_app_name(artifacts.decision),
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
    return payload


def build_ci_safe_gate_decision_payload(decision: GateDecision) -> dict[str, object]:
    """Return a GateDecision-shaped CI artifact without customer/free-form fields."""
    payload = decision.model_dump(mode="json")
    safe_metrics = {
        str(key): value
        for key, value in payload.get("metrics", {}).items()
        if isinstance(value, int | float)
    }
    payload["metrics"] = safe_metrics
    payload["reasons"] = [sanitize_text(str(item)) for item in payload.get("reasons", [])[:5]]
    payload["reason_codes"] = [
        sanitize_text(str(item)) for item in payload.get("reason_codes", [])[:10]
    ]
    payload["provenance"] = _ci_safe_provenance(payload.get("provenance"))
    payload["next_actions"] = [
        {
            "failure_category": sanitize_text(str(item.get("failure_category", ""))),
            "count": int(item.get("count", 0) or 0),
            "action": sanitize_text(str(item.get("failure_category", ""))),
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
            "action_deltas": sanitize_payload(comparison.get("action_deltas", [])),
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
    allowed_keys = {"execution_mode", "quality_pack_version", "case_set_version", "index_version"}
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
        for key in ("total_reviews", "approved", "rejected", "needs_followup", "waived_with_risk")
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
