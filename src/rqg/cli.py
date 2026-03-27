"""rqg CLI — RAG Quality Gate のコマンドラインインターフェース。

Usage:
    rqg eval   cases.csv --docs documents/ --log-dir runs/quality
    rqg check  --log-dir runs/quality --config .rqg.yml
    rqg ingest documents/
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .casegen import generate_eval_cases_from_snapshot, write_review_output
from .domain import DocumentSnapshot, EvalCase, GateDecision


def _write_json_output(path: str | Path, model: object) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    return output_path


def _write_json_list_output(path: str | Path, models: list[object]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [model.model_dump(mode="json") for model in models]
    import json

    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def _load_snapshot_from_file(path: str | Path) -> DocumentSnapshot:
    snapshot_path = Path(path)
    return DocumentSnapshot.model_validate_json(snapshot_path.read_text(encoding="utf-8"))


def _build_document_snapshot(
    *,
    source_path: Path,
    text: str,
    version: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> DocumentSnapshot:
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    snapshot_id = f"{source_path.stem}-{content_hash[:12]}"
    return DocumentSnapshot(
        snapshot_id=snapshot_id,
        doc_id=source_path.as_posix(),
        title=source_path.stem,
        source_path=source_path.as_posix(),
        content_hash=content_hash,
        created_at=datetime.now(timezone.utc),
        version=version,
        metadata=metadata or {},
    )


def _snapshot_output_path(index_dir: str | Path, snapshot: DocumentSnapshot) -> Path:
    return Path(index_dir) / "snapshots" / f"{snapshot.snapshot_id}.json"


def cmd_init_snapshot(args: argparse.Namespace) -> int:
    content_hash = hashlib.sha256(args.content.encode("utf-8")).hexdigest()
    snapshot = DocumentSnapshot(
        snapshot_id=args.snapshot_id,
        doc_id=args.doc_id,
        title=args.title,
        source_path=args.source_path,
        content_hash=content_hash,
        created_at=datetime.now(timezone.utc),
        version=args.version,
        metadata={},
    )
    output_path = _write_json_output(args.output, snapshot)
    print(f"Saved snapshot JSON to {output_path}")
    return 0


def cmd_create_sample_case(args: argparse.Namespace) -> int:
    case = EvalCase(
        case_id="sample-case-001",
        question="What policy applies to paid leave requests?",
        expected_evidence=["Paid leave requests must be submitted in advance."],
        expected_keywords=["paid leave", "advance"],
        risk_level="S2",
        doc_snapshot_id="sample-snapshot-001",
        notes="Sample case for Phase 1 scaffolding.",
    )
    output_path = _write_json_output(args.output, case)
    print(f"Saved eval case JSON to {output_path}")
    return 0


def cmd_create_sample_gate(args: argparse.Namespace) -> int:
    gate = GateDecision(
        run_id="sample-run-001",
        status="warn",
        reasons=["Sample gate decision for Phase 1 scaffolding."],
        metrics={"pass_rate": 0.8, "s1_pass_rate": 1.0},
        created_at=datetime.now(timezone.utc),
    )
    output_path = _write_json_output(args.output, gate)
    print(f"Saved gate decision JSON to {output_path}")
    return 0


def cmd_gen_cases(args: argparse.Namespace) -> int:
    snapshot_path = Path(args.snapshot)
    snapshot = _load_snapshot_from_file(snapshot_path)
    bundle = generate_eval_cases_from_snapshot(
        snapshot,
        snapshot_path=snapshot_path,
        mode=args.mode,
        max_cases=args.max_cases,
        use_llm=args.use_llm,
    )
    output_path = _write_json_list_output(args.output, bundle.cases)
    print(f"Saved {len(bundle.cases)} eval cases to {output_path}")

    if args.review_output:
        try:
            review_path = write_review_output(args.review_output, bundle.cases)
        except ValueError as exc:
            print(f"[ERROR] Failed to write review output: {exc}", file=sys.stderr)
            return 1
        print(f"Saved review output to {review_path}")
    return 0


def cmd_impact(args: argparse.Namespace) -> int:
    from .quality.impact_analysis import (
        build_impact_report,
        load_eval_cases_from_path,
        write_impact_review,
    )

    try:
        old_snapshot = _load_snapshot_from_file(args.old_snapshot)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        print(f"[ERROR] Failed to load old snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        new_snapshot = _load_snapshot_from_file(args.new_snapshot)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        print(f"[ERROR] Failed to load new snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        cases = load_eval_cases_from_path(args.cases)
    except (FileNotFoundError, ValueError, ValidationError) as exc:
        print(f"[ERROR] Failed to load cases: {exc}", file=sys.stderr)
        return 1

    reference_date: date | None = None
    if args.reference_date:
        try:
            reference_date = date.fromisoformat(args.reference_date)
        except ValueError as exc:
            print(f"[ERROR] Invalid --reference-date (expected YYYY-MM-DD): {exc}", file=sys.stderr)
            return 1

    try:
        report = build_impact_report(
            old_snapshot,
            new_snapshot,
            cases,
            old_snapshot_path=args.old_snapshot,
            new_snapshot_path=args.new_snapshot,
            reference_date=reference_date,
            strict_only=args.strict_only,
        )
    except ValueError as exc:
        print(f"[ERROR] Impact analysis failed: {exc}", file=sys.stderr)
        return 1

    output_path = _write_json_output(args.output, report)
    print(f"Saved impact report JSON to {output_path}")
    print(f"Changed evidence count: {len(report.changed_evidence_ids)}")
    print(f"Impacted case count: {len(report.impacted_case_ids)}")
    compat_state = "active" if report.legacy_compatibility_active else "inactive"
    print(f"Legacy compatibility: {compat_state}")
    print(f"Legacy compatibility matches: {report.legacy_match_count}")

    if args.review_output:
        try:
            review_path = write_impact_review(args.review_output, report)
        except ValueError as exc:
            print(f"[ERROR] Failed to write review output: {exc}", file=sys.stderr)
            return 1
        print(f"Saved impact review output to {review_path}")

    return 0


def cmd_migrate_cases(args: argparse.Namespace) -> int:
    from .quality.case_migration import (
        load_cases_with_format,
        load_snapshots,
        migrate_expected_evidence,
        write_cases_with_format,
    )

    if not args.snapshot and not args.snapshot_dir:
        print("[ERROR] Provide --snapshot and/or --snapshot-dir", file=sys.stderr)
        return 1

    try:
        snapshots = load_snapshots(args.snapshot or [], args.snapshot_dir)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        print(f"[ERROR] Failed to load snapshots: {exc}", file=sys.stderr)
        return 1

    if not snapshots:
        print("[ERROR] No snapshots found for migration", file=sys.stderr)
        return 1

    try:
        cases, payload_format = load_cases_with_format(args.cases)
    except (FileNotFoundError, ValueError, ValidationError) as exc:
        print(f"[ERROR] Failed to load cases: {exc}", file=sys.stderr)
        return 1

    migrated_cases, stats = migrate_expected_evidence(cases, snapshots)

    try:
        output_path = write_cases_with_format(args.output, migrated_cases, payload_format)
    except ValueError as exc:
        print(f"[ERROR] Failed to write migrated cases: {exc}", file=sys.stderr)
        return 1

    print(f"Saved migrated cases to {output_path}")
    print(f"Total cases: {stats['total_cases']}")
    print(f"Converted cases: {stats['converted_case_count']}")
    print(f"Total evidence refs: {stats['total_evidence_refs']}")
    print(f"Converted evidence refs: {stats['converted_evidence_refs']}")
    print(f"Unresolved legacy refs: {stats['unresolved_legacy_refs']}")

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        import json

        report_payload = {
            "snapshot_count": len(snapshots),
            **stats,
        }
        report_path.write_text(
            json.dumps(report_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved migration report to {report_path}")

    return 0


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
        if n > 0:
            snapshot = _build_document_snapshot(
                source_path=f,
                text=text,
                metadata={"chunk_count": n, "ingest_index_dir": args.index_dir},
            )
            snapshot_path = _write_json_output(
                _snapshot_output_path(args.index_dir, snapshot),
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
    """Run the quality gate check and emit stable ASCII output."""
    from .quality.check import (
        GateConfig,
        build_gate_decision,
        render_gate_markdown,
        run_check,
    )

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

    md = render_gate_markdown(result)
    print(md)
    decision = build_gate_decision(result)

    if args.output_file:
        Path(args.output_file).write_text(md, encoding="utf-8")
        print(f"Saved report to {args.output_file}")

    if args.decision_file:
        decision_path = _write_json_output(args.decision_file, decision)
        print(f"Saved gate decision JSON to {decision_path}")

    status = "PASS" if result.gate_passed else "FAIL"
    print(f"Gate: {status}")
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
    p_check.add_argument("--decision-file", default=None)

    # --- gen-cases ---
    p_gen_cases = sub.add_parser("gen-cases", help="Generate EvalCase candidates from a snapshot")
    p_gen_cases.add_argument("--snapshot", required=True, help="Path to DocumentSnapshot JSON")
    p_gen_cases.add_argument("--output", required=True, help="Path to generated EvalCase JSON")
    p_gen_cases.add_argument("--review-output", default=None, help="Optional .md review output")
    p_gen_cases.add_argument("--mode", choices=["rule", "hybrid"], default="rule")
    p_gen_cases.add_argument("--max-cases", type=int, default=50)
    p_gen_cases.add_argument("--use-llm", action="store_true", help="Use LLM question generation in addition to rule generation")

    # --- impact ---
    p_impact = sub.add_parser("impact", help="Analyze impacted eval cases between two snapshots")
    p_impact.add_argument("--old-snapshot", required=True, help="Path to old DocumentSnapshot JSON")
    p_impact.add_argument("--new-snapshot", required=True, help="Path to new DocumentSnapshot JSON")
    p_impact.add_argument("--cases", required=True, help="Path to EvalCase JSON or CSV")
    p_impact.add_argument("--output", required=True, help="Path to impact report JSON")
    p_impact.add_argument(
        "--reference-date",
        default=None,
        help="Optional simulation date (YYYY-MM-DD) for legacy compatibility window",
    )
    p_impact.add_argument(
        "--strict-only",
        action="store_true",
        help="Disable legacy compatibility matching regardless of date",
    )
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
    p_migrate_cases.add_argument("--output", required=True, help="Path to migrated cases JSON or CSV")
    p_migrate_cases.add_argument(
        "--report",
        default=None,
        help="Optional JSON summary report path",
    )

    # --- init-snapshot ---
    p_init_snapshot = sub.add_parser(
        "init-snapshot", help="Create a document snapshot JSON file"
    )
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
    p_sample_case = sub.add_parser(
        "create-sample-case", help="Create a sample eval case JSON file"
    )
    p_sample_case.add_argument("--output", required=True)

    # --- create-sample-gate ---
    p_sample_gate = sub.add_parser(
        "create-sample-gate", help="Create a sample gate decision JSON file"
    )
    p_sample_gate.add_argument("--output", required=True)

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
    elif args.command == "init-snapshot":
        return cmd_init_snapshot(args)
    elif args.command == "create-sample-case":
        return cmd_create_sample_case(args)
    elif args.command == "create-sample-gate":
        return cmd_create_sample_gate(args)
    elif args.command == "gen-cases":
        return cmd_gen_cases(args)
    elif args.command == "impact":
        return cmd_impact(args)
    elif args.command == "migrate-cases":
        return cmd_migrate_cases(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
