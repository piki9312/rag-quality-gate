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
from ..security import redact_text, sanitize_error_message, sanitize_mapping

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
) -> None:
    body = _build_payload(
        kind=target.kind,
        decision=decision,
        report_path=report_path,
        decision_path=decision_path,
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
        safe_error = sanitize_error_message(exc)
        raise RuntimeError(f"Notification delivery failed for {target.kind}: {safe_error}") from exc


def _build_payload(
    *,
    kind: NotificationKind,
    decision: GateDecision,
    report_path: str | Path | None,
    decision_path: str | Path | None,
) -> dict[str, object]:
    summary = _build_summary_text(
        decision=decision,
        report_path=report_path,
        decision_path=decision_path,
    )
    if kind in {"slack", "teams"}:
        return {"text": redact_text(summary)}
    return sanitize_mapping(
        {
            "event": "rqg.gate_decision",
            "status": decision.status,
            "policy_status": decision.policy_status,
            "run_id": decision.run_id,
            "created_at": decision.created_at.isoformat(),
            "reasons": decision.reasons,
            "metrics": decision.metrics,
            "next_actions": [item.model_dump(mode="json") for item in decision.next_actions],
            "judge_reliability": decision.judge_reliability,
            "fallback_summary": decision.fallback_summary,
            "needs_human_review": decision.needs_human_review,
            "report_path": str(report_path) if report_path else None,
            "decision_path": str(decision_path) if decision_path else None,
            "summary": summary,
        }
    )


def _build_summary_text(
    *,
    decision: GateDecision,
    report_path: str | Path | None,
    decision_path: str | Path | None,
) -> str:
    pack_name = decision.pack.pack_name if decision.pack else "unknown-pack"
    lines = [
        f"Proof Gate {decision.policy_status.upper()} for {pack_name} update.",
        f"Run: {decision.run_id}",
    ]
    s1_fail_count = int(decision.metrics.get("s1_fail_count", 0.0) or 0.0)
    lines.append(f"S1 failures: {s1_fail_count}")
    if decision.reasons:
        lines.append(f"Top reasons: {redact_text('; '.join(decision.reasons[:3]))}")
    lines.append(f"Judge reliability: {decision.judge_reliability}")
    fallback_used = decision.judge_fallback_used or decision.embedding_fallback_used
    lines.append(f"Fallback used: {'yes' if fallback_used else 'no'}")
    lines.append(f"Needs human review: {'yes' if decision.needs_human_review else 'no'}")
    if decision.next_actions:
        lines.append(f"Next action: {redact_text(decision.next_actions[0].action)}")
    if report_path:
        lines.append(f"Report: {report_path}")
    if decision_path:
        lines.append(f"Decision JSON: {decision_path}")
    return "\n".join(lines)


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
