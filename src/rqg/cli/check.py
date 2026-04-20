"""rqg check sub-command."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..quality.notifications import send_gate_notifications
from .helpers import append_jsonl_output, write_json_output, write_text_output


def cmd_check(args: argparse.Namespace) -> int:
    """Run the quality gate check and emit stable ASCII output."""
    from ..quality.check import (
        GateConfig,
        build_gate_decision,
        load_failure_actions_from_quality_pack,
        normalize_aggregation_policy,
        render_gate_markdown,
        run_check,
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
    if quality_pack_path:
        failure_actions = load_failure_actions_from_quality_pack(quality_pack_path)

    md = render_gate_markdown(result, failure_actions=failure_actions)
    print(md)
    decision = build_gate_decision(result, failure_actions=failure_actions)

    report_path = (
        Path(args.output_file) if args.output_file else Path(args.log_dir) / "gate-report.md"
    )
    report_path = write_text_output(report_path, md)
    print(f"Saved report to {report_path}")

    decision_output = (
        Path(args.decision_file)
        if args.decision_file
        else Path(args.log_dir) / "gate-decision.json"
    )
    decision_path = write_json_output(decision_output, decision)
    print(f"Saved gate decision JSON to {decision_path}")

    decision_history_path = Path(args.log_dir) / "gate-decisions.jsonl"
    appended_history = append_jsonl_output(decision_history_path, decision)
    print(f"Appended gate decision JSONL to {appended_history}")

    warnings = send_gate_notifications(
        decision,
        config_path=args.config,
        report_path=report_path,
        decision_path=decision_path,
    )
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
