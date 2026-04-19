"""rqg eval sub-command."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .helpers import reset_eval_log_dir, validate_index_dir, write_json_output


def cmd_ingest(args: argparse.Namespace) -> int:
    """文書をRAGに投入する。"""
    from ..serving.rag import RAGStore

    from .helpers import build_document_snapshot, snapshot_output_path

    if not validate_index_dir(args.index_dir):
        return 1

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
        if n > 0:
            snapshot = build_document_snapshot(
                source_path=f,
                text=text,
                metadata={"chunk_count": n, "ingest_index_dir": args.index_dir},
            )
            snapshot_path = write_json_output(
                snapshot_output_path(args.index_dir, snapshot),
                snapshot,
            )
            if args.verbose:
                print(f"  snapshot: {snapshot_path}")
        total_chunks += n
        if args.verbose:
            print(f"  {f.name}: {n} chunks")

    print(f"Ingested {total_chunks} chunks from {doc_dir}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    """テストケースを実行して品質評価する。"""
    from ..quality.loader import filter_cases_by_status, load_cases
    from ..quality.runner import RAGQualityRunner
    from ..serving.rag import RAGStore

    if not validate_index_dir(args.index_dir):
        return 1

    if args.log_dir and args.reset_log_dir:
        removed = reset_eval_log_dir(args.log_dir)
        print(f"Reset log_dir {args.log_dir}: removed {len(removed)} files")

    all_cases = load_cases(args.cases)
    cases = filter_cases_by_status(all_cases, allowed_statuses={"active"})
    if args.verbose:
        print(f"Loaded {len(all_cases)} test cases from {args.cases}")
    if len(cases) != len(all_cases):
        skipped = len(all_cases) - len(cases)
        print(
            f"Selected {len(cases)} active test cases from {args.cases} "
            f"(skipped {skipped} non-active cases)"
        )

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
