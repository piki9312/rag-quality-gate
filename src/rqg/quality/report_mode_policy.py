"""Central policy for resolving report exposure mode.

This module intentionally owns only report-mode selection and fail-fast rules.
Artifact field allowlists and reliability assessment stay in their existing
modules for now so this can be introduced as a small, compatible step.
"""

from __future__ import annotations

from dataclasses import dataclass

VALID_REPORT_MODES = {"ci", "redacted", "full"}
SIMULATION_WARNING = (
    "SIMULATION ONLY: mock/simulation output must not be used as production quality evidence."
)
GITHUB_ACTIONS_BOUNDARY_GUIDANCE = (
    "GitHub Actions may handle sample/mock/dummy data only; customer/full/external runs "
    "must be executed in a local/private runner or customer-controlled environment."
)


@dataclass(frozen=True, slots=True)
class ReportModeContext:
    requested_report_mode: object = None
    github_actions: bool = False
    customer_facing: bool = False
    execution_mode: str | None = None
    mock: bool = False
    rag_endpoint: object = None
    adapter_config: object = None
    allow_simulation_output: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedReportModePolicy:
    report_mode: str
    requested_report_mode: str | None
    github_actions: bool
    customer_facing: bool
    execution_mode: str | None
    downgraded: bool = False
    downgrade_reason: str | None = None
    blocked: bool = False
    error_message: str | None = None
    simulation: bool = False
    simulation_warning: str | None = None


def normalize_report_mode_value(value: object) -> str:
    """Normalize public report mode names while preserving existing ValueError behavior."""
    if value is None:
        return "full"

    normalized = str(value).strip().lower().replace("-", "_")
    if normalized == "":
        return "full"
    if normalized in VALID_REPORT_MODES:
        return normalized

    allowed = ", ".join(sorted(VALID_REPORT_MODES))
    raise ValueError(f"Invalid report_mode '{value}' (allowed: {allowed})")


def resolve_report_mode_policy(context: ReportModeContext) -> ResolvedReportModePolicy:
    """Resolve the effective report mode and safety boundary for a command run."""
    requested = _normalize_requested_report_mode(context.requested_report_mode)
    execution_mode = str(context.execution_mode or "").strip().lower() or None
    simulation = bool(context.mock) or execution_mode in {"mock", "ci_mock"}
    external_rag = (
        execution_mode == "external_real"
        or _has_value(context.rag_endpoint)
        or _has_value(context.adapter_config)
    )

    if context.customer_facing and simulation and not context.allow_simulation_output:
        return _blocked(
            context,
            requested,
            execution_mode,
            simulation=simulation,
            message=(
                "[ERROR] customer-facing output is blocked for mock/simulation runs unless "
                f"--allow-simulation-output is set. {SIMULATION_WARNING}"
            ),
        )

    if requested == "full":
        if context.github_actions:
            return _blocked(
                context,
                requested,
                execution_mode,
                simulation=simulation,
                message=(
                    "[ERROR] --report-mode full is not allowed when GITHUB_ACTIONS=true. "
                    f"{GITHUB_ACTIONS_BOUNDARY_GUIDANCE}"
                ),
            )
        if context.customer_facing:
            return _blocked(
                context,
                requested,
                execution_mode,
                simulation=simulation,
                message="[ERROR] --report-mode full is not allowed with --customer-facing.",
            )
        return _resolved(context, "full", requested, execution_mode, simulation=simulation)

    if requested == "redacted":
        if context.github_actions:
            return _resolved(
                context,
                "ci",
                requested,
                execution_mode,
                downgraded=True,
                downgrade_reason="GitHub Actions requires ci report mode.",
                simulation=simulation,
            )
        return _resolved(context, "redacted", requested, execution_mode, simulation=simulation)

    if requested == "ci":
        return _resolved(context, "ci", requested, execution_mode, simulation=simulation)

    if context.github_actions:
        return _resolved(context, "ci", requested, execution_mode, simulation=simulation)
    if context.customer_facing:
        return _resolved(context, "redacted", requested, execution_mode, simulation=simulation)
    if external_rag:
        return _resolved(context, "redacted", requested, execution_mode, simulation=simulation)
    return _resolved(context, "full", requested, execution_mode, simulation=simulation)


def _normalize_requested_report_mode(value: object) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().lower().replace("-", "_")
    if normalized == "":
        return None
    if normalized in VALID_REPORT_MODES:
        return normalized

    allowed = ", ".join(sorted(VALID_REPORT_MODES))
    raise ValueError(f"Invalid report_mode '{value}' (allowed: {allowed})")


def _has_value(value: object) -> bool:
    return bool(str(value or "").strip())


def _resolved(
    context: ReportModeContext,
    report_mode: str,
    requested: str | None,
    execution_mode: str | None,
    *,
    downgraded: bool = False,
    downgrade_reason: str | None = None,
    simulation: bool,
) -> ResolvedReportModePolicy:
    return ResolvedReportModePolicy(
        report_mode=report_mode,
        requested_report_mode=requested,
        github_actions=context.github_actions,
        customer_facing=context.customer_facing,
        execution_mode=execution_mode,
        downgraded=downgraded,
        downgrade_reason=downgrade_reason,
        simulation=simulation,
        simulation_warning=SIMULATION_WARNING if simulation and context.customer_facing else None,
    )


def _blocked(
    context: ReportModeContext,
    requested: str | None,
    execution_mode: str | None,
    *,
    simulation: bool,
    message: str,
) -> ResolvedReportModePolicy:
    fallback_mode = "ci" if context.github_actions else "redacted"
    return ResolvedReportModePolicy(
        report_mode=fallback_mode,
        requested_report_mode=requested,
        github_actions=context.github_actions,
        customer_facing=context.customer_facing,
        execution_mode=execution_mode,
        blocked=True,
        error_message=message,
        simulation=simulation,
        simulation_warning=SIMULATION_WARNING if simulation and context.customer_facing else None,
    )
