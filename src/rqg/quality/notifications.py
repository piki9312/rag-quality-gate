"""Gate notification delivery helpers."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ..domain import GateDecision
from ..security import (
    sanitize_artifact_path,
    sanitize_error_message,
    sanitize_payload,
    sanitize_text,
)
from .artifact_exposure_policy import ArtifactType, resolve_artifact_exposure
from .reason_taxonomy import canonical_reason
from .reporting import (
    CI_SAFE_REASON_CODES,
    CI_UNKNOWN_REASON_CODE,
    safe_relative_artifact_path,
    stable_case_ref,
)

NotificationKind = Literal["slack", "teams", "webhook"]


@dataclass(slots=True)
class NotificationTarget:
    """Notification target resolved from config."""

    kind: NotificationKind
    url: str
    notify_on: set[str] = field(default_factory=lambda: {"fail"})
    timeout_sec: float = 10.0


def load_notification_targets(config_path: str | None = None) -> list[NotificationTarget]:
    """Load notification targets from config."""
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return []

    candidates: list[Path] = []
    if config_path:
        candidates.append(Path(config_path))
    candidates.extend([Path(".rqg.yml"), Path(".rqg.yaml")])

    config_file = next((candidate for candidate in candidates if candidate.exists()), None)
    if config_file is None:
        return []

    try:
        payload = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return []

    raw_targets = payload.get("notifications", [])
    if not isinstance(raw_targets, list):
        return []

    targets: list[NotificationTarget] = []
    for item in raw_targets:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type", "webhook")).strip().lower()
        if kind not in {"slack", "teams", "webhook"}:
            continue
        url = _resolve_url(item)
        if not url:
            continue
        notify_on = _normalize_notify_on(item.get("notify_on"))
        timeout_sec = _coerce_timeout(item.get("timeout_sec"), default=10.0)
        targets.append(
            NotificationTarget(
                kind=kind,
                url=url,
                notify_on=notify_on,
                timeout_sec=timeout_sec,
            )
        )
    return targets


def send_gate_notifications(
    decision: GateDecision,
    *,
    config_path: str | None = None,
    report_path: str | Path | None = None,
    decision_path: str | Path | None = None,
    report_mode: str = "full",
) -> list[str]:
    """Send notifications for a gate decision; return delivery warnings."""
    warnings: list[str] = []
    targets = load_notification_targets(config_path)
    if not targets:
        return warnings

    for target in targets:
        if decision.status not in target.notify_on:
            continue
        try:
            _send_notification(
                target=target,
                decision=decision,
                report_path=report_path,
                decision_path=decision_path,
                report_mode=report_mode,
            )
        except RuntimeError as exc:
            warnings.append(str(exc))
    return warnings


def _send_notification(
    *,
    target: NotificationTarget,
    decision: GateDecision,
    report_path: str | Path | None = None,
    decision_path: str | Path | None = None,
    report_mode: str = "full",
) -> None:
    body = _build_payload(
        kind=target.kind,
        decision=decision,
        report_path=report_path,
        decision_path=decision_path,
        report_mode=report_mode,
    )
    request = urllib.request.Request(
        target.url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=target.timeout_sec):
            return
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(
            f"Notification delivery failed for {target.kind}: {sanitize_error_message(exc)}"
        ) from exc


def _build_payload(
    *,
    kind: NotificationKind,
    decision: GateDecision,
    report_path: str | Path | None,
    decision_path: str | Path | None,
    report_mode: str = "full",
) -> dict[str, object]:
    summary = _build_summary_text(
        decision=decision,
        report_path=report_path,
        decision_path=decision_path,
        report_mode=report_mode,
    )
    if kind in {"slack", "teams"}:
        return _project_notification_payload({"text": summary}, report_mode=report_mode)
    raw_payload = {
        "event": "rqg.gate_decision",
        "status": decision.status,
        "gate_status": decision.status,
        "policy_status": decision.policy_status,
        "run_id": decision.run_id,
        "created_at": decision.created_at.isoformat(),
        "reason_codes": _safe_reason_codes(decision),
        "safe_reason_codes": _safe_reason_codes(decision),
        "failure_type_code": _primary_reason_code(decision),
        "failure_category": _primary_reason_code(decision),
        "overall_pass_rate": _metric(decision, "overall_pass_rate"),
        "s1_pass_rate": _metric(decision, "s1_pass_rate"),
        "s1_failed_count": _metric(decision, "s1_fail_count"),
        "total_cases": _metric(decision, "current_runs"),
        "failed_cases": _failed_cases(decision),
        "needs_human_review": decision.needs_human_review,
        "case_id_hash": _affected_case_id_hashes(decision),
        "report_path": _safe_notification_artifact_path(report_path, decision_path),
        "decision_path": _safe_notification_artifact_path(decision_path, report_path),
        "execution_mode": _safe_execution_mode(decision.execution_mode),
        "report_mode": str(report_mode or "full").strip().lower() or "full",
        "summary": summary,
    }
    return _project_notification_payload(raw_payload, report_mode=report_mode)


def _build_ci_payload(
    *,
    kind: NotificationKind,
    decision: GateDecision,
    report_path: str | Path | None,
    decision_path: str | Path | None,
) -> dict[str, object]:
    # Kept for compatibility with tests or downstream imports. Notification payloads
    # now use the same external-facing projection for every report mode.
    summary = _build_ci_summary_text(
        decision=decision,
        report_path=report_path,
        decision_path=decision_path,
    )
    if kind in {"slack", "teams"}:
        return {"text": summary}
    return {
        "event": "rqg.gate_decision",
        "status": decision.status,
        "policy_status": decision.policy_status,
        "run_id": decision.run_id,
        "created_at": decision.created_at.isoformat(),
        "reason_codes": [sanitize_text(item) for item in decision.reason_codes[:10]],
        "metrics": decision.metrics,
        "needs_human_review": decision.needs_human_review,
        "report_path": sanitize_artifact_path(report_path),
        "decision_path": sanitize_artifact_path(decision_path),
        "summary": summary,
    }


def _build_ci_summary_text(
    *,
    decision: GateDecision,
    report_path: str | Path | None,
    decision_path: str | Path | None,
) -> str:
    s1_fail_count = int(decision.metrics.get("s1_fail_count", 0.0) or 0.0)
    lines = [
        f"Proof Gate {decision.policy_status.upper()}",
        f"Run: {decision.run_id}",
        f"Gate status: {decision.status.upper()}",
        f"Policy status: {decision.policy_status.upper()}",
        f"S1 failures: {s1_fail_count}",
        f"Needs human review: {'yes' if decision.needs_human_review else 'no'}",
    ]
    if decision.reason_codes:
        safe_codes = [sanitize_text(code) for code in decision.reason_codes[:5]]
        lines.append(f"Reason codes: {', '.join(safe_codes)}")
    if report_path:
        lines.append(f"Report: {sanitize_artifact_path(report_path)}")
    if decision_path:
        lines.append(f"Decision JSON: {sanitize_artifact_path(decision_path)}")
    return "\n".join(lines)


def _build_summary_text(
    *,
    decision: GateDecision,
    report_path: str | Path | None,
    decision_path: str | Path | None,
    report_mode: str = "full",
) -> str:
    reason_codes = _safe_reason_codes(decision)
    s1_fail_count = int(_metric(decision, "s1_fail_count") or 0.0)
    lines = [
        f"Proof Gate {decision.policy_status.upper()}",
        f"Run: {decision.run_id}",
        f"Gate status: {decision.status.upper()}",
        f"Policy status: {decision.policy_status.upper()}",
        f"Report mode: {str(report_mode or 'full').strip().lower() or 'full'}",
    ]
    lines.append(f"S1 failures: {s1_fail_count}")
    lines.append(f"Needs human review: {'yes' if decision.needs_human_review else 'no'}")
    if reason_codes:
        lines.append(f"Reason codes: {', '.join(reason_codes[:5])}")
    if report_path:
        lines.append(f"Report: {_safe_notification_artifact_path(report_path, decision_path)}")
    if decision_path:
        lines.append(f"Decision JSON: {_safe_notification_artifact_path(decision_path, report_path)}")
    return "\n".join(lines)


def _safe_reason_summaries(decision: GateDecision) -> list[str]:
    categories = [
        sanitize_text(item.failure_category)
        for item in decision.next_actions
        if str(item.failure_category).strip()
    ]
    if categories:
        return categories
    return [sanitize_text(reason) for reason in decision.reasons[:3]]


def _safe_next_actions(decision: GateDecision) -> list[dict[str, object]]:
    safe_items: list[dict[str, object]] = []
    for item in decision.next_actions:
        safe_items.append(
            {
                "failure_category": sanitize_text(item.failure_category),
                "count": item.count,
                "action": sanitize_text(item.action),
                "owner": sanitize_text(item.owner),
                "due": sanitize_text(item.due),
                "affected_case_ids": [sanitize_text(case_id) for case_id in item.affected_case_ids],
            }
        )
    return safe_items


def _project_notification_payload(
    payload: dict[str, object],
    *,
    report_mode: str,
) -> dict[str, object]:
    policy = resolve_artifact_exposure(ArtifactType.NOTIFICATION_PAYLOAD, report_mode)
    projected: dict[str, object] = {}
    for key, value in payload.items():
        if policy.allows(key):
            projected[key] = sanitize_payload(value)
    return projected


def _safe_reason_codes(decision: GateDecision) -> list[str]:
    raw_values: list[object] = [*decision.reason_codes]
    raw_values.extend(item.failure_category for item in decision.next_actions)
    if decision.judge_fallback_used:
        raw_values.append("judge_fallback_used")
    if decision.embedding_fallback_used:
        raw_values.append("embedding_fallback_used")
    if decision.needs_human_review:
        raw_values.append("needs_human_review")

    codes: list[str] = []
    for value in raw_values:
        code = canonical_reason(value)
        if code not in CI_SAFE_REASON_CODES:
            code = CI_UNKNOWN_REASON_CODE
        if code not in codes:
            codes.append(code)
    return codes


def _primary_reason_code(decision: GateDecision) -> str:
    codes = _safe_reason_codes(decision)
    return codes[0] if codes else CI_UNKNOWN_REASON_CODE


def _metric(decision: GateDecision, key: str) -> float | None:
    value = decision.metrics.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _failed_cases(decision: GateDecision) -> float | None:
    if "failed_cases" in decision.metrics:
        return _metric(decision, "failed_cases")
    return _metric(decision, "s1_fail_count")


def _affected_case_id_hashes(decision: GateDecision) -> list[str]:
    hashes: list[str] = []
    for item in decision.next_actions:
        for case_id in item.affected_case_ids:
            if not case_id:
                continue
            case_hash = stable_case_ref(case_id)
            if case_hash not in hashes:
                hashes.append(case_hash)
    return hashes


def _safe_notification_artifact_path(
    path: str | Path | None,
    sibling_path: str | Path | None = None,
) -> str | None:
    if path is None:
        return None
    artifact_path = Path(path)
    base_dir = Path(sibling_path).parent if sibling_path is not None else artifact_path.parent
    if sibling_path is not None:
        return safe_relative_artifact_path(artifact_path, base_dir)
    if artifact_path.is_absolute():
        return safe_relative_artifact_path(artifact_path, base_dir)
    sanitized = sanitize_artifact_path(path)
    if sanitized and any(part in {".tmp", "tmp"} for part in Path(sanitized).parts):
        return Path(sanitized).name
    return sanitized


def _safe_execution_mode(value: object) -> str:
    normalized = str(value or "").strip().lower()
    allowed = {"real", "mock", "simulation", "external_real", "external_rag"}
    return normalized if normalized in allowed else "unknown"


def _resolve_url(item: dict[str, object]) -> str | None:
    direct = item.get("webhook_url")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    env_name = item.get("webhook_url_env")
    if isinstance(env_name, str) and env_name.strip():
        return os.environ.get(env_name.strip())
    return None


def _normalize_notify_on(value: object) -> set[str]:
    allowed = {"pass", "warn", "fail"}
    if not isinstance(value, list):
        return {"fail"}
    normalized = {
        str(item).strip().lower() for item in value if str(item).strip().lower() in allowed
    }
    return normalized or {"fail"}


def _coerce_timeout(value: object, *, default: float) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        return default
    return timeout if timeout > 0 else default
