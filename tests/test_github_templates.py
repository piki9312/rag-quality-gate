from __future__ import annotations

from pathlib import Path

import yaml


def _load_yaml(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _find_step(payload: dict, job_name: str, step_name: str) -> dict:
    for step in payload["jobs"][job_name]["steps"]:
        if step.get("name", "") == step_name:
            return step
    raise AssertionError(f"step not found: {job_name}/{step_name}")


def test_reusable_gate_template_declares_workflow_call_contract() -> None:
    path = Path("templates/github/workflows/rqg-reusable-gate.yml")
    payload = _load_yaml(path)

    assert payload["name"] == "RQG Reusable Gate"
    assert "workflow_call" in payload["on"]

    workflow_call = payload["on"]["workflow_call"]
    inputs = workflow_call["inputs"]
    outputs = workflow_call["outputs"]

    assert "cases_path" in inputs
    assert "rqg_install_command" in inputs
    assert "run_pack_validation" in inputs
    assert "pack_validation_preset" in inputs
    assert "pack_dir" in inputs
    assert "run_connection_validation" in inputs
    assert "notification_kind" in inputs

    assert "gate_status" in outputs
    assert "gate_run_id" in outputs
    assert "gate_decision_path" in outputs
    assert "gate_report_path" in outputs
    assert "gate_report_json_path" in outputs
    assert "pack_validation_ok" in outputs
    assert "pack_validation_path" in outputs
    assert "connection_ok" in outputs
    assert "connection_validation_path" in outputs
    assert "gate_history_summary_path" in outputs

    step_names = [step.get("name", "") for step in payload["jobs"]["rqg_gate"]["steps"]]
    assert "Preflight configuration" in step_names
    assert "Validate pack onboarding" in step_names
    assert "Validate external RAG connection" in step_names
    assert "Run gate" in step_names
    assert "Collect gate outputs" in step_names


def test_python_shell_steps_in_templates_compile() -> None:
    workflow_paths = [
        Path("templates/github/workflows/rqg-reusable-gate.yml"),
        Path("templates/github/workflows/rqg-onboarding.yml"),
        Path("templates/github/rqg-gate-weekly-review.yml"),
        Path(".github/workflows/rqg-reusable-gate.yml"),
    ]

    for workflow_path in workflow_paths:
        payload = _load_yaml(workflow_path)
        for job_name, job in payload.get("jobs", {}).items():
            for step in job.get("steps", []):
                if step.get("shell") != "python" or "run" not in step:
                    continue
                compile(
                    step["run"],
                    f"{workflow_path.as_posix()}::{job_name}::{step.get('name', '<unnamed>')}",
                    "exec",
                )


def test_reusable_gate_template_normalizes_pack_relative_overrides() -> None:
    payload = _load_yaml(Path("templates/github/workflows/rqg-reusable-gate.yml"))

    validate_pack_step = _find_step(payload, "rqg_gate", "Validate pack onboarding")
    run_script = validate_pack_step["run"]

    assert "def normalize_pack_override" in run_script
    assert 'cases_path = normalize_pack_override("CASES_PATH", pack_dir)' in run_script
    assert (
        'gate_config_path = normalize_pack_override("PACK_GATE_CONFIG_PATH", pack_dir)'
        in run_script
    )
    assert (
        'quality_pack_path = normalize_pack_override("QUALITY_PACK_PATH", pack_dir)' in run_script
    )
    assert 'docs_dir = normalize_pack_override("DOCS_DIR", pack_dir)' in run_script


def test_template_callers_use_reusable_gate_workflow() -> None:
    expected_presets = {
        "rqg-gate-mock.yml": "local_docs",
        "rqg-gate-external.yml": "external",
        "rqg-gate-external-notify.yml": "external_notify",
        "rqg-gate-weekly-review.yml": "external",
    }
    for template_name in [
        "rqg-gate-mock.yml",
        "rqg-gate-external.yml",
        "rqg-gate-external-notify.yml",
        "rqg-gate-weekly-review.yml",
    ]:
        payload = _load_yaml(Path("templates/github") / template_name)
        job = payload["jobs"]["rqg-gate"]
        assert job["uses"] == "./.github/workflows/rqg-reusable-gate.yml"
        assert job["with"]["run_pack_validation"] == "true"
        assert job["with"]["pack_validation_preset"] == expected_presets[template_name]
        assert job["with"]["pack_dir"] == "packs/hr"


def test_weekly_review_template_downloads_artifact_and_exports_issue_payload() -> None:
    payload = _load_yaml(Path("templates/github/rqg-gate-weekly-review.yml"))

    assert "weekly-review-followup" in payload["jobs"]
    followup_job = payload["jobs"]["weekly-review-followup"]
    step_names = [step.get("name", "") for step in followup_job["steps"]]
    assert "Download gate artifacts" in step_names
    assert "Resolve weekly review source" in step_names
    assert "Export weekly review issue payload" in step_names
    assert "Upsert weekly review issue" in step_names
    assert "Add issue to triage board" in step_names
    assert "Send optional Slack summary (Block Kit)" in step_names

    resolve_step = _find_step(payload, "weekly-review-followup", "Resolve weekly review source")
    assert "gate_report_json_path" in resolve_step["run"]
    assert "--bundle-file" in resolve_step["run"]
    assert "--summary-file" in resolve_step["run"]


def test_repo_reusable_gate_workflow_matches_template() -> None:
    repo_workflow = Path(".github/workflows/rqg-reusable-gate.yml").read_text(encoding="utf-8")
    template_workflow = Path("templates/github/workflows/rqg-reusable-gate.yml").read_text(
        encoding="utf-8"
    )

    assert repo_workflow.rstrip() == template_workflow.rstrip()


def test_repo_mock_workflow_uses_reusable_gate_workflow() -> None:
    payload = _load_yaml(Path(".github/workflows/rqg-gate-mock.yml"))
    job = payload["jobs"]["rqg-gate"]

    assert job["uses"] == "./.github/workflows/rqg-reusable-gate.yml"
    assert job["with"]["run_pack_validation"] == "true"
    assert job["with"]["pack_validation_preset"] == "local_docs"
    assert job["with"]["pack_dir"] == "packs/hr"
    assert job["with"]["notification_kind"] == "slack"
    assert job["with"]["notify_on"] == "fail"
    assert job["secrets"]["notification_webhook_url"] == "${{ secrets.RQG_SLACK_WEBHOOK_URL }}"


def test_phase4_weekly_gate_repo_workflow_has_optional_slack_summary() -> None:
    payload = _load_yaml(Path(".github/workflows/phase4-weekly-gate.yml"))

    workflow_dispatch_inputs = payload["on"]["workflow_dispatch"]["inputs"]
    assert workflow_dispatch_inputs["force_slack_test"]["type"] == "boolean"
    assert workflow_dispatch_inputs["force_slack_test"]["default"] == "false"

    step_names = [step.get("name", "") for step in payload["jobs"]["weekly-gate"]["steps"]]
    assert "Send optional Slack summary" in step_names

    slack_step = _find_step(payload, "weekly-gate", "Send optional Slack summary")
    assert slack_step["env"]["SLACK_WEBHOOK_URL"] == "${{ secrets.RQG_SLACK_WEBHOOK_URL }}"
    assert (
        slack_step["env"]["FORCE_SLACK_TEST"]
        == "${{ github.event.inputs.force_slack_test || 'false' }}"
    )
    compile(
        slack_step["run"],
        ".github/workflows/phase4-weekly-gate.yml::weekly-gate::Send optional Slack summary",
        "exec",
    )


def test_phase2_5_weekly_review_repo_workflows_use_fixed_title_and_labels() -> None:
    issue_workflow = Path(".github/workflows/phase2-5-weekly-review-issue.yml").read_text(
        encoding="utf-8"
    )
    metrics_workflow = Path(".github/workflows/phase2-5-weekly-metrics.yml").read_text(
        encoding="utf-8"
    )

    assert "[Phase2.5][Weekly Review]" in issue_workflow
    assert "'phase2-5', 'weekly-review', 'ops'" in issue_workflow
    assert "[Phase2.5][Weekly Review]" in metrics_workflow
    assert "'phase2-5', 'weekly-review', 'ops'" in metrics_workflow


def test_phase2_5_weekly_metrics_repo_workflow_has_optional_slack_summary() -> None:
    payload = _load_yaml(Path(".github/workflows/phase2-5-weekly-metrics.yml"))

    step_names = [
        step.get("name", "") for step in payload["jobs"]["phase2-5-weekly-metrics"]["steps"]
    ]
    assert "Send optional weekly review Slack summary" in step_names

    slack_step = _find_step(
        payload, "phase2-5-weekly-metrics", "Send optional weekly review Slack summary"
    )
    assert slack_step["env"]["SLACK_WEBHOOK_URL"] == "${{ secrets.RQG_SLACK_WEBHOOK_URL }}"
    compile(
        slack_step["run"],
        ".github/workflows/phase2-5-weekly-metrics.yml::phase2-5-weekly-metrics::Send optional weekly review Slack summary",
        "exec",
    )


def test_template_readme_mentions_reusable_workflow_outputs() -> None:
    readme = Path("templates/github/README.md").read_text(encoding="utf-8")

    assert "rqg-reusable-gate.yml" in readme
    assert "gate_status" in readme
    assert "pack_validation_ok" in readme
    assert "pack-validation.json" in readme
    assert "connection_ok" in readme
    assert "gate_report_json_path" in readme
    assert "gate-report.json" in readme
    assert "gate_history_summary_path" in readme
    assert "gate-history-summary.json" in readme
    assert "rqg-gate-weekly-review.yml" in readme
    assert "[Phase2.5][Weekly Review] YYYY-MM-DD" in readme
    assert "RQG_TRIAGE_PROJECT_ID" in readme
    assert "repository secrets" in readme
    assert "run_pack_validation" in readme
    assert "pack_validation_preset" in readme


def test_onboarding_template_runs_pack_validation() -> None:
    payload = _load_yaml(Path("templates/github/workflows/rqg-onboarding.yml"))

    step_names = [step.get("name", "") for step in payload["jobs"]["onboarding-smoke"]["steps"]]
    assert "Validate pack configuration" in step_names
