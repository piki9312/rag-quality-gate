from __future__ import annotations

import pytest

from rqg.quality.report_mode_policy import (
    ReportModeContext,
    resolve_report_mode_policy,
)


def test_github_actions_requested_full_is_fail_fast() -> None:
    policy = resolve_report_mode_policy(
        ReportModeContext(requested_report_mode="full", github_actions=True)
    )

    assert policy.blocked is True
    assert policy.report_mode == "ci"
    assert "--report-mode full is not allowed" in str(policy.error_message)


def test_customer_facing_requested_full_is_fail_fast() -> None:
    policy = resolve_report_mode_policy(
        ReportModeContext(requested_report_mode="full", customer_facing=True)
    )

    assert policy.blocked is True
    assert policy.report_mode == "redacted"
    assert "--customer-facing" in str(policy.error_message)


def test_customer_facing_unspecified_defaults_to_redacted() -> None:
    policy = resolve_report_mode_policy(ReportModeContext(customer_facing=True))

    assert policy.blocked is False
    assert policy.report_mode == "redacted"


def test_external_rag_unspecified_defaults_to_redacted() -> None:
    by_endpoint = resolve_report_mode_policy(
        ReportModeContext(rag_endpoint="https://rag.example.test/search")
    )
    by_execution_mode = resolve_report_mode_policy(
        ReportModeContext(execution_mode="external_real")
    )
    by_adapter_config = resolve_report_mode_policy(
        ReportModeContext(adapter_config="adapter_config.yml")
    )

    assert by_endpoint.report_mode == "redacted"
    assert by_execution_mode.report_mode == "redacted"
    assert by_adapter_config.report_mode == "redacted"


def test_requested_redacted_downgrades_to_ci_in_github_actions() -> None:
    policy = resolve_report_mode_policy(
        ReportModeContext(requested_report_mode="redacted", github_actions=True)
    )

    assert policy.report_mode == "ci"
    assert policy.downgraded is True
    assert policy.downgrade_reason


def test_requested_ci_is_always_ci() -> None:
    policy = resolve_report_mode_policy(
        ReportModeContext(
            requested_report_mode="ci",
            github_actions=False,
            customer_facing=True,
            execution_mode="external_real",
            mock=True,
            allow_simulation_output=True,
        )
    )

    assert policy.blocked is False
    assert policy.report_mode == "ci"


def test_customer_facing_mock_without_override_is_fail_fast() -> None:
    policy = resolve_report_mode_policy(
        ReportModeContext(customer_facing=True, mock=True, allow_simulation_output=False)
    )

    assert policy.blocked is True
    assert policy.report_mode == "redacted"
    assert "--allow-simulation-output" in str(policy.error_message)


def test_customer_facing_mock_with_override_is_redacted_with_warning() -> None:
    policy = resolve_report_mode_policy(
        ReportModeContext(customer_facing=True, mock=True, allow_simulation_output=True)
    )

    assert policy.blocked is False
    assert policy.report_mode == "redacted"
    assert policy.simulation_warning
    assert "SIMULATION ONLY" in policy.simulation_warning


def test_invalid_report_mode_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Invalid report_mode"):
        resolve_report_mode_policy(ReportModeContext(requested_report_mode="private"))
