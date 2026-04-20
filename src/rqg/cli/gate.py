"""rqg gate sub-command — combines eval + check in one step."""

from __future__ import annotations

import argparse

from .check import cmd_check
from .eval import cmd_eval
from .helpers import validate_index_dir


def cmd_gate(args: argparse.Namespace) -> int:
    """Run eval and check in one command."""
    if not validate_index_dir(args.index_dir):
        return 1

    print("=== Step 1/2: eval ===")
    eval_exit = cmd_eval(
        argparse.Namespace(
            cases=args.cases,
            docs=args.docs,
            index_dir=args.index_dir,
            log_dir=args.log_dir,
            reset_log_dir=args.reset_log_dir,
            context_k=args.context_k,
            mock=args.mock,
            verbose=args.verbose,
        )
    )

    if eval_exit not in (0, 1):
        return eval_exit

    print("\n=== Step 2/2: check ===")
    check_exit = cmd_check(
        argparse.Namespace(
            log_dir=args.log_dir,
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
            warn_exit_code=args.warn_exit_code,
        )
    )
    return check_exit
