"""rqg check sub-command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..quality.notifications import send_gate_notifications
from .helpers import github_actions_enabled


def _exit_code_for_gate_result(*, policy_status: str, gate_status: str, warn_exit_code: int) -> int:
    normalized_policy = str(policy_status or "").strip().lower()
    normalized_gate = str(gate_status or "").strip().lower()

    if normalized_policy == "block":
        return 1
    if normalized_policy in {"warn", "needs_human_review"}:
        return warn_exit_code
    if normalized_gate == "fail":
        return 1
    if normalized_gate == "warn":
        return warn_exit_code
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Run the quality gate check and emit stable ASCII output."""
    from ..quality.case_merge import load_csv_rows
    from ..quality.case_schema import normalize_legacy_row, validate_case_rows
    from ..quality.check import (
        GateConfig,
        build_gate_decision,
        load_failure_actions_from_quality_pack,
        load_quality_pack_payload,
        load_review_steward_from_quality_pack,
        normalize_aggregation_policy,
        render_customer_summary_markdown,
        render_gate_markdown,
        run_check,
    )
    from ..quality.comparison import (
        build_before_after_summary,
        load_gate_bundle,
        render_before_after_summary_markdown,
    )
    from ..quality.history import build_gate_history_summary_payload, load_gate_decision_history
    from ..quality.provenance import (
        SIMULATION_WARNING_EN,
        SIMULATION_WARNING_JA,
        is_simulation_execution_mode,
        load_change_event,
        load_manual_review_records,
    )
    from ..quality.report_mode_policy import ReportModeContext, resolve_report_mode_policy
    from ..quality.reporting import (
        BundleJsonReportAdapter,
        DecisionHistoryJsonlReportAdapter,
        DecisionJsonReportAdapter,
        GateReportArtifacts,
        HistorySummaryJsonReportAdapter,
        MarkdownFileReportAdapter,
        safe_relative_artifact_path,
    )

    try:
        github_actions = github_actions_enabled()
        requested_report_mode = getattr(args, "report_mode", None)
        early_report_policy = resolve_report_mode_policy(
            ReportModeContext(
                requested_report_mode=requested_report_mode,
                github_actions=github_actions,
                customer_facing=bool(getattr(args, "customer_facing", False)),
                mock=bool(getattr(args, "mock", False)),
                allow_simulation_output=bool(
                    getattr(args, "allow_simulation_output", False)
                ),
            )
        )
        if early_report_policy.blocked:
            print(early_report_policy.error_message, file=sys.stderr)
            return 1

        if args.config and Path(args.config).exists():
            config = GateConfig.from_yaml(args.config)
        else:
            config = GateConfig(
                s1_pass_rate=args.s1_threshold,
                overall_pass_rate=args.overall_threshold,
                max_overall_drop_pct=args.max_overall_drop_pct or 0.0,
                max_s1_drop_pct=args.max_s1_drop_pct or 0.0,
                aggregation_policy=normalize_aggregation_policy(args.aggregation_policy),
            )

        if args.aggregation_policy is not None:
            config.aggregation_policy = normalize_aggregation_policy(args.aggregation_policy)
    except ValueError as exc:
        print(f"[ERROR] Failed to load gate config: {exc}", file=sys.stderr)
        return 1

    if args.max_overall_drop_pct is not None:
        config.max_overall_drop_pct = args.max_overall_drop_pct
    if args.max_s1_drop_pct is not None:
        config.max_s1_drop_pct = args.max_s1_drop_pct

    if getattr(args, "strict_s1_governance", False) and args.cases_file:
        # This intentionally duplicates strict validation done in validate-pack as
        # defense in depth, so a direct `rqg check` invocation cannot bypass S1 safety
        # checks even if earlier validation steps were skipped.
        try:
            rows = [normalize_legacy_row(row) for row in load_csv_rows(args.cases_file)]
        except FileNotFoundError as exc:
            print(f"[ERROR] strict S1 governance cases file not found: {exc}", file=sys.stderr)
            return 1
        except ValueError as exc:
            print(f"[ERROR] strict S1 governance cases file is invalid: {exc}", file=sys.stderr)
            return 1
        issues = validate_case_rows(rows, strict_s1_governance=True)
        blocking = [issue for issue in issues if issue.level == "error"]
        if blocking:
            for issue in blocking:
                print(
                    f"[ERROR] strict S1 governance: {issue.case_id} {issue.field}: {issue.message}"
                )
            return 1

    result = run_check(
        log_dir=args.log_dir,
        config=config,
        days=args.days,
        baseline_dir=args.baseline_dir,
        baseline_days=args.baseline_days,
        cases_file=args.cases_file,
    )
    try:
        report_policy = resolve_report_mode_policy(
            ReportModeContext(
                requested_report_mode=requested_report_mode,
                github_actions=github_actions,
                customer_facing=bool(getattr(args, "customer_facing", False)),
                execution_mode=result.execution_mode,
                mock=bool(getattr(args, "mock", False)),
                allow_simulation_output=bool(
                    getattr(args, "allow_simulation_output", False)
                ),
            )
        )
    except ValueError as exc:
        print(f"[ERROR] Failed to load gate config: {exc}", file=sys.stderr)
        return 1
    if report_policy.blocked:
        print(report_policy.error_message, file=sys.stderr)
        return 1
    report_mode = report_policy.report_mode

    try:
        change_event = load_change_event(getattr(args, "change_event_file", None))
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    if change_event and not result.run_provenance.get("change_event_id"):
        result.run_provenance = {
            **result.run_provenance,
            "change_event": change_event,
            **change_event,
        }
    if getattr(args, "customer_facing", False) and is_simulation_execution_mode(
        result.execution_mode
    ):
        if not getattr(args, "allow_simulation_output", False):
            print(
                "[ERROR] customer-facing output is blocked for mock/simulation runs unless "
                "--allow-simulation-output is set. "
                f"{SIMULATION_WARNING_EN} {SIMULATION_WARNING_JA}",
                file=sys.stderr,
            )
            return 1
    manual_review_records = load_manual_review_records(getattr(args, "manual_review_file", None))
    manual_review_summary = {
        "total_reviews": len(manual_review_records),
        "approved": sum(
            1 for item in manual_review_records if item.get("review_status") == "approved"
        ),
        "rejected": sum(
            1 for item in manual_review_records if item.get("review_status") == "rejected"
        ),
        "needs_followup": sum(
            1 for item in manual_review_records if item.get("review_status") == "needs_followup"
        ),
        "waived_with_risk": sum(
            1 for item in manual_review_records if item.get("review_status") == "waived_with_risk"
        ),
        "records": manual_review_records,
    }

    quality_pack_path = args.quality_pack
    if not quality_pack_path and args.config:
        inferred_quality_pack = Path(args.config).with_name("quality-pack.yml")
        if inferred_quality_pack.exists():
            quality_pack_path = str(inferred_quality_pack)

    failure_actions: dict[str, str] = {}
    review_steward: str | None = None
    pack_metadata: dict[str, object] | None = None
    if quality_pack_path:
        failure_actions = load_failure_actions_from_quality_pack(quality_pack_path)
        review_steward = load_review_steward_from_quality_pack(quality_pack_path)
        pack_payload = load_quality_pack_payload(quality_pack_path)
        raw_pack_metadata = pack_payload.get("pack", {}) if isinstance(pack_payload, dict) else {}
        if isinstance(raw_pack_metadata, dict):
            pack_metadata = raw_pack_metadata

    decision_history_path = Path(args.log_dir) / "gate-decisions.jsonl"
    append_history = getattr(args, "append_history", True)
    notifications_enabled = getattr(args, "notifications_enabled", True)
    decision = build_gate_decision(
        result,
        failure_actions=failure_actions,
        pack_metadata=pack_metadata,
        manual_review_summary=manual_review_summary,
    )
    history_decisions = [*load_gate_decision_history(decision_history_path), decision]
    history_summary_payload = build_gate_history_summary_payload(
        history_decisions,
        stale_cases=result.stale_cases,
        stale_after_days=result.stale_after_days,
        fresh_case_review_rate=result.fresh_case_review_rate,
        fresh_case_count=result.fresh_case_count,
        fresh_case_total=result.fresh_case_total,
        review_steward=review_steward,
    )

    md = render_gate_markdown(
        result,
        failure_actions=failure_actions,
        pack_metadata=pack_metadata,
        history_decisions=history_decisions,
        report_mode=report_mode,
    )
    customer_summary_md = render_customer_summary_markdown(
        result,
        failure_actions=failure_actions,
        pack_metadata=pack_metadata,
        report_mode=report_mode,
    )
    if report_mode == "ci":
        print(md.rstrip())
    else:
        print(md)

    default_report_name = "gate-report-ci.md" if report_mode == "ci" else "gate-report.md"
    default_bundle_name = "gate-report-ci.json" if report_mode == "ci" else "gate-report.json"
    report_path = (
        Path(args.output_file) if args.output_file else Path(args.log_dir) / default_report_name
    )
    customer_summary_path = Path(args.log_dir) / "customer-summary.md"
    history_summary_path = Path(args.log_dir) / "gate-history-summary.json"
    decision_path = (
        Path(args.decision_file)
        if args.decision_file
        else Path(args.log_dir) / "gate-decision.json"
    )
    bundle_path = (
        Path(args.bundle_file)
        if getattr(args, "bundle_file", None)
        else Path(args.log_dir) / default_bundle_name
    )
    artifacts = GateReportArtifacts(
        markdown=md,
        customer_summary_markdown=customer_summary_md,
        decision=decision,
        history_summary=history_summary_payload,
        report_path=report_path,
        customer_summary_path=customer_summary_path,
        decision_path=decision_path,
        history_summary_path=history_summary_path,
        history_path=decision_history_path,
        bundle_path=bundle_path,
        check_result=result,
        report_mode=report_mode,
    )

    report_path = MarkdownFileReportAdapter(report_path).emit(artifacts)
    if report_mode != "ci":
        print(f"Saved report to {report_path}")
    customer_summary_path = MarkdownFileReportAdapter(customer_summary_path).emit(
        GateReportArtifacts(
            markdown=customer_summary_md,
            customer_summary_markdown=customer_summary_md,
            decision=decision,
            history_summary=history_summary_payload,
            report_path=customer_summary_path,
            customer_summary_path=customer_summary_path,
            decision_path=decision_path,
            history_summary_path=history_summary_path,
            history_path=decision_history_path,
            bundle_path=bundle_path,
            check_result=result,
            report_mode=report_mode,
        )
    )
    if report_mode != "ci":
        print(f"Saved customer summary to {customer_summary_path}")

    history_summary_path = HistorySummaryJsonReportAdapter(history_summary_path).emit(artifacts)
    if report_mode != "ci":
        print(f"Saved history summary JSON to {history_summary_path}")

    decision_path = DecisionJsonReportAdapter(decision_path).emit(artifacts)
    if report_mode != "ci":
        print(f"Saved gate decision JSON to {decision_path}")

    bundle_path = BundleJsonReportAdapter(bundle_path).emit(artifacts)
    if report_mode != "ci":
        print(f"Saved report bundle JSON to {bundle_path}")

    appended_history = DecisionHistoryJsonlReportAdapter(
        decision_history_path,
        enabled=append_history,
    ).emit(artifacts)
    if report_mode == "ci":
        artifact_base_dir = bundle_path.parent
        artifact_refs = [
            safe_relative_artifact_path(report_path, artifact_base_dir),
            safe_relative_artifact_path(history_summary_path, artifact_base_dir),
            safe_relative_artifact_path(decision_path, artifact_base_dir),
            safe_relative_artifact_path(bundle_path, artifact_base_dir),
        ]
        print(f"Artifact refs: {', '.join(artifact_refs)}")
    elif appended_history is not None:
        print(f"Appended gate decision JSONL to {appended_history}")
    else:
        print("Skipped gate decision JSONL append")

    baseline_bundle = load_gate_bundle(getattr(args, "baseline_bundle", None))
    if baseline_bundle:
        current_bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        comparison_summary = build_before_after_summary(
            before_bundle=baseline_bundle,
            after_bundle=current_bundle,
        )
        comparison_json_path = Path(args.log_dir) / "before-after-summary.json"
        comparison_md_path = Path(args.log_dir) / "before-after-summary.md"
        comparison_json_path.write_text(
            json.dumps(comparison_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        comparison_md_path.write_text(
            render_before_after_summary_markdown(comparison_summary),
            encoding="utf-8",
        )
        if report_mode != "ci":
            print(f"Saved before/after summary JSON to {comparison_json_path}")
            print(f"Saved before/after summary Markdown to {comparison_md_path}")

    warnings = []
    if notifications_enabled:
        warnings = send_gate_notifications(
            decision,
            config_path=args.config,
            report_path=report_path,
            decision_path=decision_path,
            report_mode=report_mode,
        )
    else:
        if report_mode != "ci":
            print("Skipped notifications")
    for warning in warnings:
        if report_mode == "ci":
            print("[WARN] notification warning omitted in ci report mode")
        else:
            print(f"[WARN] {warning}")

    status = result.gate_status.upper()
    policy_status = decision.policy_status.upper()
    print(f"Gate: {status}")
    print(f"Policy: {policy_status}")

    warn_exit_code = getattr(args, "warn_exit_code", 0)
    return _exit_code_for_gate_result(
        policy_status=decision.policy_status,
        gate_status=result.gate_status,
        warn_exit_code=warn_exit_code,
    )
