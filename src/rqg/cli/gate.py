"""rqg gate sub-command — combines eval + check in one step."""

from __future__ import annotations

import argparse
import sys

from .check import cmd_check
from .eval import cmd_eval
from .helpers import (
    build_dry_run_log_dir,
    github_actions_enabled,
    github_actions_fail_fast_message,
    validate_index_dir,
)


def cmd_gate(args: argparse.Namespace) -> int:
    """Run eval and check in one command."""
    requested_report_mode = str(getattr(args, "report_mode", "") or "").strip().lower()
    if getattr(args, "customer_facing", False) and getattr(args, "mock", False):
        if not getattr(args, "allow_simulation_output", False):
            print(
                "[ERROR] --customer-facing cannot be used with --mock unless "
                "--allow-simulation-output is set. "
                "Mock output is simulation only and must not be treated as customer quality evidence.",
                file=sys.stderr,
            )
            return 1
        print(
            "[WARN] customer-facing simulation output enabled; the resulting artifact will be marked "
            "SIMULATION ONLY and must not be used as production quality evidence.",
            file=sys.stderr,
        )
    if github_actions_enabled():
        if requested_report_mode == "full":
            print(
                github_actions_fail_fast_message(
                    "--report-mode full is not allowed when GITHUB_ACTIONS=true."
                ),
                file=sys.stderr,
            )
            return 1
        if getattr(args, "rag_endpoint", None) or getattr(args, "adapter_config", None):
            print(
                github_actions_fail_fast_message(
                    "External/customer RAG execution is not allowed when GITHUB_ACTIONS=true."
                ),
                file=sys.stderr,
            )
            return 1

    # Skip index-dir validation when using external RAG
    rag_endpoint = getattr(args, "rag_endpoint", None)
    adapter_config = getattr(args, "adapter_config", None)
    if not rag_endpoint and not adapter_config and not validate_index_dir(args.index_dir):
        return 1

    gate_log_dir = args.log_dir
    check_append_history = True
    notifications_enabled = True
    if getattr(args, "dry_run", False):
        gate_log_dir = build_dry_run_log_dir(args.log_dir).as_posix()
        check_append_history = False
        notifications_enabled = False
        print(f"Dry run mode: using isolated log_dir {gate_log_dir}")
        print("Dry run mode: notifications disabled; gate history will not be appended")

    print("=== Step 1/2: eval ===")
    eval_exit = cmd_eval(
        argparse.Namespace(
            cases=args.cases,
            docs=args.docs,
            index_dir=args.index_dir,
            log_dir=gate_log_dir,
            reset_log_dir=args.reset_log_dir,
            context_k=args.context_k,
            mock=args.mock,
            rag_endpoint=getattr(args, "rag_endpoint", None),
            rag_api_key_env=getattr(args, "rag_api_key_env", None),
            adapter_config=getattr(args, "adapter_config", None),
            report_mode=getattr(args, "report_mode", None),
            verbose=args.verbose,
            customer_facing=getattr(args, "customer_facing", False),
        )
    )

    if eval_exit not in (0, 1):
        return eval_exit

    print("\n=== Step 2/2: check ===")
    check_exit = cmd_check(
        argparse.Namespace(
            log_dir=gate_log_dir,
            config=args.config,
            days=args.days,
            baseline_dir=args.baseline_dir,
            baseline_days=args.baseline_days,
            cases_file=args.cases_file or args.cases,
            quality_pack=args.quality_pack,
            s1_threshold=args.s1_threshold,
            overall_threshold=args.overall_threshold,
            max_overall_drop_pct=args.max_overall_drop_pct,
            max_s1_drop_pct=args.max_s1_drop_pct,
            aggregation_policy=args.aggregation_policy,
            output_file=args.output_file,
            decision_file=args.decision_file,
            bundle_file=getattr(args, "bundle_file", None),
            report_mode=getattr(args, "report_mode", None),
            customer_facing=getattr(args, "customer_facing", False),
            allow_simulation_output=getattr(args, "allow_simulation_output", False),
            strict_s1_governance=getattr(args, "strict_s1_governance", False),
            change_event_file=getattr(args, "change_event_file", None),
            review_stage=getattr(args, "review_stage", None),
            manual_review_file=getattr(args, "manual_review_file", None),
            baseline_bundle=getattr(args, "baseline_bundle", None),
            warn_exit_code=args.warn_exit_code,
            append_history=check_append_history,
            notifications_enabled=notifications_enabled,
        )
    )
    return check_exit
