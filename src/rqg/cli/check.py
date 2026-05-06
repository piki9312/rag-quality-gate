"""rqg check sub-command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..quality.notifications import send_gate_notifications
from .helpers import github_actions_enabled, github_actions_fail_fast_message


def cmd_check(args: argparse.Namespace) -> int:
    """Run the quality gate check and emit stable ASCII output."""
    from ..quality.check import (
        GateConfig,
        build_gate_decision,
        load_failure_actions_from_quality_pack,
        load_quality_pack_payload,
        load_review_steward_from_quality_pack,
        normalize_aggregation_policy,
        normalize_report_mode,
        render_gate_markdown,
        run_check,
    )
    from ..quality.history import build_gate_history_summary_payload, load_gate_decision_history
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
        report_mode = normalize_report_mode(
            "ci" if github_actions and requested_report_mode is None else requested_report_mode
        )
        if github_actions and requested_report_mode == "full":
            print(
                github_actions_fail_fast_message(
                    "--report-mode full is not allowed when GITHUB_ACTIONS=true."
                ),
                file=sys.stderr,
            )
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

    result = run_check(
        log_dir=args.log_dir,
        config=config,
        days=args.days,
        baseline_dir=args.baseline_dir,
        baseline_days=args.baseline_days,
        cases_file=args.cases_file,
    )

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
    if report_mode == "ci":
        print(md.rstrip())
    else:
        print(md)

    report_path = (
        Path(args.output_file) if args.output_file else Path(args.log_dir) / "gate-report.md"
    )
    history_summary_path = Path(args.log_dir) / "gate-history-summary.json"
    decision_path = (
        Path(args.decision_file)
        if args.decision_file
        else Path(args.log_dir) / "gate-decision.json"
    )
    bundle_path = (
        Path(args.bundle_file)
        if getattr(args, "bundle_file", None)
        else Path(args.log_dir) / "gate-report.json"
    )
    artifacts = GateReportArtifacts(
        markdown=md,
        decision=decision,
        history_summary=history_summary_payload,
        report_path=report_path,
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
        if appended_history is not None:
            artifact_refs.append(safe_relative_artifact_path(appended_history, artifact_base_dir))
        print(f"Artifact refs: {', '.join(artifact_refs)}")
    elif appended_history is not None:
        print(f"Appended gate decision JSONL to {appended_history}")
    else:
        print("Skipped gate decision JSONL append")

    warnings = []
    if notifications_enabled:
        warnings = send_gate_notifications(
            decision,
            config_path=args.config,
            report_path=report_path,
            decision_path=decision_path,
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
    if decision.policy_status == "block":
        return 1
    if decision.policy_status in {"warn", "needs_human_review"}:
        return warn_exit_code
    if result.gate_status == "fail":
        return 1
    if result.gate_status == "warn":
        return warn_exit_code
    return 0
