"""rqg check sub-command."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..quality.notifications import send_gate_notifications


def cmd_check(args: argparse.Namespace) -> int:
    """Run the quality gate check and emit stable ASCII output."""
    from ..quality.history import build_gate_history_summary_payload, load_gate_decision_history
    from ..quality.check import (
        GateConfig,
        build_gate_decision,
        load_failure_actions_from_quality_pack,
        load_review_steward_from_quality_pack,
        normalize_aggregation_policy,
        render_gate_markdown,
        run_check,
    )
    from ..quality.reporting import (
        BundleJsonReportAdapter,
        DecisionHistoryJsonlReportAdapter,
        DecisionJsonReportAdapter,
        GateReportArtifacts,
        HistorySummaryJsonReportAdapter,
        MarkdownFileReportAdapter,
    )

    try:
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
        import sys

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
    if quality_pack_path:
        failure_actions = load_failure_actions_from_quality_pack(quality_pack_path)
        review_steward = load_review_steward_from_quality_pack(quality_pack_path)

    decision_history_path = Path(args.log_dir) / "gate-decisions.jsonl"
    append_history = getattr(args, "append_history", True)
    notifications_enabled = getattr(args, "notifications_enabled", True)
    decision = build_gate_decision(result, failure_actions=failure_actions)
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
        history_decisions=history_decisions,
    )
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
    )

    report_path = MarkdownFileReportAdapter(report_path).emit(artifacts)
    print(f"Saved report to {report_path}")

    history_summary_path = HistorySummaryJsonReportAdapter(history_summary_path).emit(artifacts)
    print(f"Saved history summary JSON to {history_summary_path}")

    decision_path = DecisionJsonReportAdapter(decision_path).emit(artifacts)
    print(f"Saved gate decision JSON to {decision_path}")

    bundle_path = BundleJsonReportAdapter(bundle_path).emit(artifacts)
    print(f"Saved report bundle JSON to {bundle_path}")

    appended_history = DecisionHistoryJsonlReportAdapter(
        decision_history_path,
        enabled=append_history,
    ).emit(artifacts)
    if appended_history is not None:
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
        print("Skipped notifications")
    for warning in warnings:
        print(f"[WARN] {warning}")

    status = result.gate_status.upper()
    print(f"Gate: {status}")

    warn_exit_code = getattr(args, "warn_exit_code", 0)
    if result.gate_status == "fail":
        return 1
    if result.gate_status == "warn":
        return warn_exit_code
    return 0
