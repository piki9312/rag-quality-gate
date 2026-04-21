"""rqg CLI — RAG Quality Gate のコマンドラインインターフェース。

Usage:
    rqg eval   cases.csv --docs documents/ --log-dir runs/quality
    rqg check  --log-dir runs/quality --config .rqg.yml
    rqg ingest documents/
    rqg init-pack packs/my_pack
    rqg init-pack packs/my_pack --profile demo_cycle
    rqg init-pack packs/my_pack --profile wiki
    rqg init-pack --list-profiles
"""

from __future__ import annotations

import argparse
import logging
import sys

from .casegen import (
    cmd_gen_cases,
    cmd_impact,
    cmd_merge_cases,
    cmd_migrate_cases,
    cmd_validate_cases,
)
from .check import cmd_check
from .eval import cmd_eval, cmd_ingest
from .export_weekly_review import cmd_export_weekly_review
from .gate import cmd_gate
from .history import cmd_history
from .pack import cmd_init_pack
from .scaffold import cmd_create_sample_case, cmd_create_sample_gate, cmd_init_snapshot
from .validate_connection import cmd_validate_connection
from .validate_pack import cmd_validate_pack


def build_parser() -> argparse.ArgumentParser:
    """CLI パーサーを構築して返す。テストからも利用可能。"""
    parser = argparse.ArgumentParser(
        prog="rqg",
        description="RAG Quality Gate - regression testing for RAG systems",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command")

    # --- ingest ---
    p_ingest = sub.add_parser("ingest", help="Ingest documents into RAG store")
    p_ingest.add_argument("docs_dir", metavar="docs", help="Directory containing documents")
    p_ingest.add_argument("--index-dir", default="index")

    # --- eval ---
    p_eval = sub.add_parser("eval", help="Run quality evaluation")
    p_eval.add_argument("cases", help="Path to test cases CSV")
    p_eval.add_argument("--docs", help="Documents directory (auto-ingest if store empty)")
    p_eval.add_argument("--index-dir", default="index")
    p_eval.add_argument("--log-dir", default="runs/quality")
    p_eval.add_argument(
        "--reset-log-dir",
        action="store_true",
        help="Remove existing eval/check artifacts in log-dir before running eval",
    )
    p_eval.add_argument("--context-k", type=int, default=3)
    p_eval.add_argument("--mock", action="store_true", help="Use mock LLM (no API key needed)")
    p_eval.add_argument(
        "--rag-endpoint",
        default=None,
        help="External RAG API endpoint URL. When set, uses HTTP adapter instead of local FAISS.",
    )
    p_eval.add_argument(
        "--rag-api-key-env",
        default=None,
        help="Environment variable name containing API key for external RAG endpoint.",
    )

    # --- gate ---
    p_gate = sub.add_parser("gate", help="Run eval + check in one command")
    p_gate.add_argument("cases", help="Path to test cases CSV")
    p_gate.add_argument("--docs", help="Documents directory (auto-ingest if store empty)")
    p_gate.add_argument("--index-dir", default="index")
    p_gate.add_argument("--log-dir", default="runs/quality")
    p_gate.add_argument(
        "--reset-log-dir",
        action="store_true",
        help="Remove existing eval/check artifacts in log-dir before running eval",
    )
    p_gate.add_argument("--context-k", type=int, default=3)
    p_gate.add_argument("--mock", action="store_true", help="Use mock LLM (no API key needed)")
    p_gate.add_argument(
        "--rag-endpoint",
        default=None,
        help="External RAG API endpoint URL. When set, uses HTTP adapter instead of local FAISS.",
    )
    p_gate.add_argument(
        "--rag-api-key-env",
        default=None,
        help="Environment variable name containing API key for external RAG endpoint.",
    )
    p_gate.add_argument("--config", help="Path to .rqg.yml config")
    p_gate.add_argument("--days", type=int, default=1)
    p_gate.add_argument(
        "--aggregation-policy",
        default=None,
        choices=["latest_run", "window"],
        help="How to aggregate current/baseline records before gate evaluation (default: latest_run)",
    )
    p_gate.add_argument("--baseline-dir", default=None)
    p_gate.add_argument("--baseline-days", type=int, default=7)
    p_gate.add_argument("--cases-file", default=None)
    p_gate.add_argument(
        "--quality-pack",
        default=None,
        help="Optional path to quality-pack.yml for failure next-action hints",
    )
    p_gate.add_argument("--s1-threshold", type=float, default=100.0)
    p_gate.add_argument("--overall-threshold", type=float, default=80.0)
    p_gate.add_argument(
        "--max-overall-drop-pct",
        type=float,
        default=None,
        help="Optional max allowed overall pass-rate drop vs baseline (percentage points)",
    )
    p_gate.add_argument(
        "--max-s1-drop-pct",
        type=float,
        default=None,
        help="Optional max allowed S1 pass-rate drop vs baseline (percentage points)",
    )
    p_gate.add_argument(
        "--output-file",
        default=None,
        help="Optional markdown report path (default: <log-dir>/gate-report.md)",
    )
    p_gate.add_argument(
        "--decision-file",
        default=None,
        help="Optional gate decision JSON path (default: <log-dir>/gate-decision.json)",
    )
    p_gate.add_argument(
        "--bundle-file",
        default=None,
        help="Optional consolidated JSON bundle path (default: <log-dir>/gate-report.json)",
    )
    p_gate.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the gate in an isolated dry-run log_dir without notifications or history append",
    )
    p_gate.add_argument(
        "--warn-exit-code",
        type=int,
        default=0,
        help="Exit code when gate status is warn (default: 0, set to 1 to block on warn)",
    )

    # --- check ---
    p_check = sub.add_parser("check", help="Run quality gate check")
    p_check.add_argument("--log-dir", default="runs/quality")
    p_check.add_argument("--config", help="Path to .rqg.yml config")
    p_check.add_argument("--days", type=int, default=1)
    p_check.add_argument(
        "--aggregation-policy",
        default=None,
        choices=["latest_run", "window"],
        help="How to aggregate current/baseline records before gate evaluation (default: latest_run)",
    )
    p_check.add_argument("--baseline-dir", default=None)
    p_check.add_argument("--baseline-days", type=int, default=7)
    p_check.add_argument("--cases-file", default=None)
    p_check.add_argument(
        "--quality-pack",
        default=None,
        help="Optional path to quality-pack.yml for failure next-action hints",
    )
    p_check.add_argument("--s1-threshold", type=float, default=100.0)
    p_check.add_argument("--overall-threshold", type=float, default=80.0)
    p_check.add_argument(
        "--max-overall-drop-pct",
        type=float,
        default=None,
        help="Optional max allowed overall pass-rate drop vs baseline (percentage points)",
    )
    p_check.add_argument(
        "--max-s1-drop-pct",
        type=float,
        default=None,
        help="Optional max allowed S1 pass-rate drop vs baseline (percentage points)",
    )
    p_check.add_argument(
        "--output-file",
        default=None,
        help="Optional markdown report path (default: <log-dir>/gate-report.md)",
    )
    p_check.add_argument(
        "--decision-file",
        default=None,
        help="Optional gate decision JSON path (default: <log-dir>/gate-decision.json)",
    )
    p_check.add_argument(
        "--bundle-file",
        default=None,
        help="Optional consolidated JSON bundle path (default: <log-dir>/gate-report.json)",
    )
    p_check.add_argument(
        "--warn-exit-code",
        type=int,
        default=0,
        help="Exit code when gate status is warn (default: 0, set to 1 to block on warn)",
    )

    # --- history ---
    p_history = sub.add_parser("history", help="Show recent gate decision history")
    p_history.add_argument("--log-dir", default="runs/quality")
    p_history.add_argument("--last", type=int, default=10)
    p_history.add_argument(
        "--compare-offset",
        type=int,
        default=1,
        help="Compare the latest decision with N entries back (default: 1)",
    )
    p_history.add_argument(
        "--trend-window",
        type=int,
        default=5,
        help="Number of recent entries used for trend summary (default: 5)",
    )
    p_history.add_argument(
        "--status",
        choices=["pass", "warn", "fail"],
        default=None,
        help="Filter history rows by status",
    )
    p_history.add_argument(
        "--output-file",
        default=None,
        help="Optional markdown output path for history report",
    )

    # --- export-weekly-review ---
    p_export_weekly_review = sub.add_parser(
        "export-weekly-review",
        help="Export a GitHub issue payload from gate-history-summary.json",
    )
    p_export_weekly_review.add_argument(
        "--summary-file",
        default=None,
        help="Path to gate-history-summary.json (default: <log-dir>/gate-history-summary.json)",
    )
    p_export_weekly_review.add_argument(
        "--log-dir",
        default="runs/quality",
        help="Log directory used when --summary-file is omitted",
    )
    p_export_weekly_review.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: alongside summary file as weekly-review-issue.json)",
    )
    p_export_weekly_review.add_argument(
        "--title-prefix",
        default="[Phase2.5][Weekly Review]",
        help="Issue title prefix",
    )
    p_export_weekly_review.add_argument(
        "--title-suffix",
        default="",
        help="Optional issue title suffix",
    )
    p_export_weekly_review.add_argument(
        "--week-start",
        default=None,
        help="Optional week_start override (YYYY-MM-DD)",
    )
    p_export_weekly_review.add_argument(
        "--label",
        action="append",
        default=None,
        help="Repeatable GitHub label value (default: phase2-5, weekly-review, ops)",
    )

    # --- validate-connection ---
    p_validate_connection = sub.add_parser(
        "validate-connection",
        help="Validate an external HTTP RAG endpoint before running gate",
    )
    p_validate_connection.add_argument("--endpoint", required=True)
    p_validate_connection.add_argument(
        "--query",
        default="healthcheck",
        help="Probe query to send to the external RAG endpoint",
    )
    p_validate_connection.add_argument("--top-k", type=int, default=3)
    p_validate_connection.add_argument("--api-key-env", default=None)
    p_validate_connection.add_argument("--timeout-sec", type=float, default=10.0)
    p_validate_connection.add_argument(
        "--output",
        default=None,
        help="Optional output path (.json or .md)",
    )

    # --- gen-cases ---
    p_gen_cases = sub.add_parser("gen-cases", help="Generate EvalCase candidates from a snapshot")
    p_gen_cases.add_argument("--snapshot", required=True, help="Path to DocumentSnapshot JSON")
    p_gen_cases.add_argument("--output", required=True, help="Path to generated EvalCase JSON")
    p_gen_cases.add_argument(
        "--review-output",
        default=None,
        help="Optional .md/.csv review output (.csv is ops-ready for cases.csv curation)",
    )
    p_gen_cases.add_argument("--mode", choices=["rule", "hybrid"], default="rule")
    p_gen_cases.add_argument("--max-cases", type=int, default=50)
    p_gen_cases.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM question generation in addition to rule generation",
    )
    p_gen_cases.add_argument(
        "--use-llm-answer-drafts",
        action="store_true",
        help="Opt in to LLM expected_answer drafts when extract-only drafting cannot fill one",
    )

    # --- impact ---
    p_impact = sub.add_parser("impact", help="Analyze impacted eval cases between two snapshots")
    p_impact.add_argument("--old-snapshot", required=True, help="Path to old DocumentSnapshot JSON")
    p_impact.add_argument("--new-snapshot", required=True, help="Path to new DocumentSnapshot JSON")
    p_impact.add_argument("--cases", required=True, help="Path to EvalCase JSON or CSV")
    p_impact.add_argument("--output", required=True, help="Path to impact report JSON")
    p_impact.add_argument(
        "--review-output",
        default=None,
        help="Optional .md review output",
    )

    # --- migrate-cases ---
    p_migrate_cases = sub.add_parser(
        "migrate-cases",
        help="Convert legacy expected_evidence to doc_id-based IDs",
    )
    p_migrate_cases.add_argument("--cases", required=True, help="Path to EvalCase JSON or CSV")
    p_migrate_cases.add_argument(
        "--snapshot",
        action="append",
        default=[],
        help="Path to DocumentSnapshot JSON (repeatable)",
    )
    p_migrate_cases.add_argument(
        "--snapshot-dir",
        default=None,
        help="Directory containing DocumentSnapshot JSON files",
    )
    p_migrate_cases.add_argument(
        "--output", required=True, help="Path to migrated cases JSON or CSV"
    )
    p_migrate_cases.add_argument(
        "--report",
        default=None,
        help="Optional JSON summary report path",
    )

    # --- merge-cases ---
    p_merge_cases = sub.add_parser(
        "merge-cases",
        help="Merge generated review CSV into operations cases.csv",
    )
    p_merge_cases.add_argument(
        "--cases",
        required=True,
        help="Path to existing operations cases.csv",
    )
    p_merge_cases.add_argument(
        "--review",
        required=True,
        help="Path to generated review CSV",
    )
    p_merge_cases.add_argument(
        "--output",
        default=None,
        help="Path to merged cases CSV (required unless --in-place or --dry-run)",
    )
    p_merge_cases.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite --cases with merged result",
    )
    p_merge_cases.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute merge and print summary without writing CSV",
    )
    p_merge_cases.add_argument(
        "--report",
        default=None,
        help="Optional JSON merge summary report path",
    )
    p_merge_cases.add_argument(
        "--validate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Validate merged rows before writing (default: on; --no-validate to skip)",
    )

    # --- validate-cases ---
    p_validate_cases = sub.add_parser(
        "validate-cases",
        help="Validate a cases.csv and report errors/warnings",
    )
    p_validate_cases.add_argument(
        "--cases",
        required=True,
        help="Path to cases.csv to validate",
    )
    p_validate_cases.add_argument(
        "--gate-config",
        default=None,
        help="Optional gate.yml used for staleness-related validation (default: sibling gate.yml when present)",
    )

    # --- validate-pack ---
    p_validate_pack = sub.add_parser(
        "validate-pack",
        help="Validate a pack for onboarding before the first gate run",
    )
    p_validate_pack.add_argument(
        "--pack-dir",
        required=True,
        help="Pack root directory (for example: packs/hr)",
    )
    p_validate_pack.add_argument(
        "--cases",
        default=None,
        help="Optional cases.csv override (default: from quality-pack.yml or <pack-dir>/cases.csv)",
    )
    p_validate_pack.add_argument(
        "--gate-config",
        default=None,
        help="Optional gate.yml override (default: from quality-pack.yml or <pack-dir>/gate.yml)",
    )
    p_validate_pack.add_argument(
        "--quality-pack",
        default=None,
        help="Optional quality-pack.yml override (default: <pack-dir>/quality-pack.yml)",
    )
    p_validate_pack.add_argument(
        "--docs-dir",
        default=None,
        help="Optional documents/ override (default: from quality-pack.yml or <pack-dir>/documents)",
    )
    p_validate_pack.add_argument(
        "--endpoint",
        default=None,
        help="Optional external RAG endpoint for external-mode onboarding validation",
    )
    p_validate_pack.add_argument(
        "--api-key-env",
        default=None,
        help="Environment variable name containing the API key for --endpoint",
    )
    p_validate_pack.add_argument(
        "--required-env",
        action="append",
        default=None,
        help="Repeatable environment variable name that must be set during onboarding",
    )
    p_validate_pack.add_argument(
        "--connection-query",
        default="healthcheck",
        help="Probe query for external connection validation",
    )
    p_validate_pack.add_argument(
        "--connection-top-k",
        type=int,
        default=3,
        help="top_k value used for external connection validation",
    )
    p_validate_pack.add_argument(
        "--connection-timeout-sec",
        type=float,
        default=10.0,
        help="Timeout in seconds for external connection validation",
    )
    p_validate_pack.add_argument(
        "--output",
        default=None,
        help="Optional output path (.json for structured output, otherwise text summary)",
    )

    # --- init-snapshot ---
    p_init_snapshot = sub.add_parser("init-snapshot", help="Create a document snapshot JSON file")
    p_init_snapshot.add_argument("--snapshot-id", required=True)
    p_init_snapshot.add_argument("--doc-id", required=True)
    p_init_snapshot.add_argument("--title", required=True)
    p_init_snapshot.add_argument("--source-path", required=True)
    p_init_snapshot.add_argument(
        "--content",
        default="Sample document content",
        help="Raw content used only to derive content_hash for the scaffold",
    )
    p_init_snapshot.add_argument("--version", default=None)
    p_init_snapshot.add_argument("--output", required=True)

    # --- create-sample-case ---
    p_sample_case = sub.add_parser("create-sample-case", help="Create a sample eval case JSON file")
    p_sample_case.add_argument("--output", required=True)

    # --- create-sample-gate ---
    p_sample_gate = sub.add_parser(
        "create-sample-gate", help="Create a sample gate decision JSON file"
    )
    p_sample_gate.add_argument("--output", required=True)

    # --- init-pack ---
    p_init_pack = sub.add_parser(
        "init-pack",
        help="Initialize a pack directory from bundled templates/profiles",
    )
    p_init_pack.add_argument(
        "output_dir",
        nargs="?",
        help="Destination path for the new pack (required unless --list-profiles)",
    )
    p_init_pack.add_argument(
        "--profile",
        choices=["demo_cycle", "sample", "hr", "wiki"],
        default="demo_cycle",
        help="Template profile to scaffold (default: demo_cycle; alias: sample)",
    )
    p_init_pack.add_argument(
        "--list-profiles",
        action="store_true",
        help="List available init-pack profiles and exit",
    )
    p_init_pack.add_argument(
        "--force",
        action="store_true",
        help="Overwrite target directory if it already exists",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.command == "ingest":
        return cmd_ingest(args)
    elif args.command == "eval":
        return cmd_eval(args)
    elif args.command == "gate":
        return cmd_gate(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "history":
        return cmd_history(args)
    elif args.command == "export-weekly-review":
        return cmd_export_weekly_review(args)
    elif args.command == "init-snapshot":
        return cmd_init_snapshot(args)
    elif args.command == "create-sample-case":
        return cmd_create_sample_case(args)
    elif args.command == "create-sample-gate":
        return cmd_create_sample_gate(args)
    elif args.command == "init-pack":
        return cmd_init_pack(args)
    elif args.command == "gen-cases":
        return cmd_gen_cases(args)
    elif args.command == "impact":
        return cmd_impact(args)
    elif args.command == "migrate-cases":
        return cmd_migrate_cases(args)
    elif args.command == "merge-cases":
        return cmd_merge_cases(args)
    elif args.command == "validate-cases":
        return cmd_validate_cases(args)
    elif args.command == "validate-pack":
        return cmd_validate_pack(args)
    elif args.command == "validate-connection":
        return cmd_validate_connection(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
