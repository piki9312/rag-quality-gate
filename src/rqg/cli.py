"""rqg CLI — RAG Quality Gate のコマンドラインインターフェース。

Usage:
    rqg eval   cases.csv --docs documents/ --log-dir runs/quality
    rqg check  --log-dir runs/quality --config .rqg.yml
    rqg ingest documents/
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def cmd_ingest(args: argparse.Namespace) -> int:
    """文書をRAGに投入する。"""
    from .serving.rag import RAGStore

    store = RAGStore(index_dir=args.index_dir)
    doc_dir = Path(args.docs_dir)
    if not doc_dir.exists():
        print(f"[ERROR] Directory not found: {doc_dir}", file=sys.stderr)
        return 1

    total_chunks = 0
    for f in sorted(doc_dir.glob("**/*")):
        if f.suffix.lower() not in {".txt", ".md"}:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        n = store.add_text(source=f.name, text=text)
        total_chunks += n
        if args.verbose:
            print(f"  {f.name}: {n} chunks")

    print(f"Ingested {total_chunks} chunks from {doc_dir}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    """テストケースを実行して品質評価する。"""
    from .quality.loader import load_cases
    from .quality.runner import RAGQualityRunner
    from .serving.rag import RAGStore

    cases = load_cases(args.cases)
    if args.verbose:
        print(f"Loaded {len(cases)} test cases from {args.cases}")

    store = RAGStore(index_dir=args.index_dir)
    if store.index is None:
        # 文書がまだ投入されていない場合、--docs から投入
        if args.docs:
            cmd_ingest_args = argparse.Namespace(
                docs_dir=args.docs,
                index_dir=args.index_dir,
                verbose=args.verbose,
            )
            cmd_ingest(cmd_ingest_args)
            # Reload store
            store = RAGStore(index_dir=args.index_dir)

    runner = RAGQualityRunner(
        store=store,
        context_k=args.context_k,
        mock_llm=args.mock,
    )

    run = runner.run_all(cases)

    # 結果表示
    print(f"\n=== RAG Quality Eval ===")
    print(f"Run ID  : {run.run_id}")
    print(f"Total   : {run.total}")
    print(f"Passed  : {run.passed}")
    print(f"Failed  : {run.failed}")
    print(f"Pass Rate: {run.pass_rate:.1f}%")

    if run.failed > 0:
        print(f"\n--- Failures ---")
        for r in run.results:
            if not r.passed:
                print(f"  [{r.case_id}] {r.severity} {r.failure_type}: {r.failure_reason}")

    # JSONL 保存
    if args.log_dir:
        jsonl_file = RAGQualityRunner.save_jsonl(run, cases, args.log_dir)
        print(f"\nSaved → {jsonl_file}")

    return 0 if run.failed == 0 else 1


def cmd_check(args: argparse.Namespace) -> int:
    """品質ゲート判定を実行する。"""
    from .quality.check import GateConfig, render_gate_markdown, run_check

    if args.config and Path(args.config).exists():
        config = GateConfig.from_yaml(args.config)
    else:
        config = GateConfig(
            s1_pass_rate=args.s1_threshold,
            overall_pass_rate=args.overall_threshold,
        )

    result = run_check(
        log_dir=args.log_dir,
        config=config,
        days=args.days,
        baseline_dir=args.baseline_dir,
        baseline_days=args.baseline_days,
        cases_file=args.cases_file,
    )

    # Markdown output
    md = render_gate_markdown(result)
    print(md)

    if args.output_file:
        Path(args.output_file).write_text(md, encoding="utf-8")
        print(f"Saved → {args.output_file}")

    status = "PASS" if result.gate_passed else "FAIL"
    print(f"Gate: {'✅' if result.gate_passed else '🔴'} {status}")
    return 0 if result.gate_passed else 1


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
    p_eval.add_argument("--context-k", type=int, default=3)
    p_eval.add_argument("--mock", action="store_true", help="Use mock LLM (no API key needed)")

    # --- check ---
    p_check = sub.add_parser("check", help="Run quality gate check")
    p_check.add_argument("--log-dir", default="runs/quality")
    p_check.add_argument("--config", help="Path to .rqg.yml config")
    p_check.add_argument("--days", type=int, default=1)
    p_check.add_argument("--baseline-dir", default=None)
    p_check.add_argument("--baseline-days", type=int, default=7)
    p_check.add_argument("--cases-file", default=None)
    p_check.add_argument("--s1-threshold", type=float, default=100.0)
    p_check.add_argument("--overall-threshold", type=float, default=80.0)
    p_check.add_argument("--output-file", default=None)

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
    elif args.command == "check":
        return cmd_check(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
