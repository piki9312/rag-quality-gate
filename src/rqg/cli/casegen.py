"""rqg casegen / impact / migrate-cases / merge-cases / validate-cases sub-commands."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from pydantic import ValidationError

from .helpers import (
    format_validation_errors,
    load_snapshot_from_file,
    write_json_data_output,
    write_json_list_output,
    write_json_output,
)


def cmd_gen_cases(args: argparse.Namespace) -> int:
    from ..casegen import generate_eval_cases_from_snapshot, write_review_output

    snapshot_path = Path(args.snapshot)
    snapshot = load_snapshot_from_file(snapshot_path)
    bundle = generate_eval_cases_from_snapshot(
        snapshot,
        snapshot_path=snapshot_path,
        mode=args.mode,
        max_cases=args.max_cases,
        use_llm=args.use_llm,
    )
    output_path = write_json_list_output(args.output, bundle.cases)
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
    from ..quality.impact_analysis import (
        build_impact_report,
        load_eval_cases_from_path,
        write_impact_review,
    )

    try:
        old_snapshot = load_snapshot_from_file(args.old_snapshot)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        print(f"[ERROR] Failed to load old snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        new_snapshot = load_snapshot_from_file(args.new_snapshot)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        print(f"[ERROR] Failed to load new snapshot: {exc}", file=sys.stderr)
        return 1

    try:
        cases = load_eval_cases_from_path(args.cases)
    except (FileNotFoundError, ValueError, ValidationError) as exc:
        print(f"[ERROR] Failed to load cases: {exc}", file=sys.stderr)
        return 1

    try:
        report = build_impact_report(
            old_snapshot,
            new_snapshot,
            cases,
            old_snapshot_path=args.old_snapshot,
            new_snapshot_path=args.new_snapshot,
        )
    except ValueError as exc:
        print(f"[ERROR] Impact analysis failed: {exc}", file=sys.stderr)
        return 1

    output_path = write_json_output(args.output, report)
    print(f"Saved impact report JSON to {output_path}")
    print(f"Changed evidence count: {len(report.changed_evidence_ids)}")
    print(f"Impacted case count: {len(report.impacted_case_ids)}")

    if args.review_output:
        try:
            review_path = write_impact_review(args.review_output, report)
        except ValueError as exc:
            print(f"[ERROR] Failed to write review output: {exc}", file=sys.stderr)
            return 1
        print(f"Saved impact review output to {review_path}")

    return 0


def cmd_migrate_cases(args: argparse.Namespace) -> int:
    from ..quality.case_migration import (
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
        report_payload = {
            "snapshot_count": len(snapshots),
            **stats,
        }
        report_path = write_json_data_output(args.report, report_payload)
        print(f"Saved migration report to {report_path}")

    return 0


def cmd_validate_cases(args: argparse.Namespace) -> int:
    from ..quality.case_merge import load_csv_rows
    from ..quality.case_schema import validate_case_rows

    try:
        rows = load_csv_rows(args.cases)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] Failed to load cases CSV: {exc}", file=sys.stderr)
        return 1

    errors = validate_case_rows(rows)
    if not errors:
        print(f"OK: {len(rows)} cases validated with no issues.")
        return 0

    err_msgs, warn_msgs = format_validation_errors(errors)
    for msg in warn_msgs:
        print(msg, file=sys.stderr)
    for msg in err_msgs:
        print(msg, file=sys.stderr)

    print(
        f"\nValidation finished: {len(err_msgs)} error(s), {len(warn_msgs)} warning(s) "
        f"in {len(rows)} cases.",
        file=sys.stderr,
    )
    return 1 if err_msgs else 0


def cmd_merge_cases(args: argparse.Namespace) -> int:
    from ..quality.case_merge import (
        load_csv_rows,
        merge_cases_rows,
        write_cases_csv,
        write_merge_report,
    )
    from ..quality.case_schema import validate_case_rows

    if args.in_place and args.output:
        print(
            "[ERROR] --in-place and --output cannot be used together",
            file=sys.stderr,
        )
        return 1

    if not args.in_place and not args.output and not args.dry_run:
        print(
            "[ERROR] Provide --output, or use --in-place, or run with --dry-run",
            file=sys.stderr,
        )
        return 1

    try:
        base_rows = load_csv_rows(args.cases)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] Failed to load base cases CSV: {exc}", file=sys.stderr)
        return 1

    try:
        review_rows = load_csv_rows(args.review)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] Failed to load review CSV: {exc}", file=sys.stderr)
        return 1

    try:
        merged_rows, summary = merge_cases_rows(base_rows, review_rows)
    except ValueError as exc:
        print(f"[ERROR] Merge failed: {exc}", file=sys.stderr)
        return 1

    if args.validate:
        v_errors = validate_case_rows(merged_rows)
        if v_errors:
            err_msgs, warn_msgs = format_validation_errors(v_errors)
            for msg in warn_msgs:
                print(msg, file=sys.stderr)
            for msg in err_msgs:
                print(msg, file=sys.stderr)
            if err_msgs:
                print(
                    f"\n[ERROR] Validation failed: {len(err_msgs)} error(s). "
                    "Merged CSV was NOT written. Use --no-validate to skip.",
                    file=sys.stderr,
                )
                return 1

    output_path: Path | None = None
    if not args.dry_run:
        output_target = Path(args.cases) if args.in_place else Path(args.output)
        output_path = write_cases_csv(output_target, merged_rows)
        print(f"Saved merged cases CSV to {output_path}")

    print(f"Base cases: {summary.base_cases}")
    print(f"Review cases: {summary.review_cases}")
    print(f"Merged cases: {summary.merged_cases}")
    print(f"Added cases: {len(summary.added_case_ids)}")
    print(f"Updated cases: {len(summary.updated_case_ids)}")
    print(f"Unchanged cases: {len(summary.unchanged_case_ids)}")
    print("Matched by content (not added): " f"{len(summary.matched_by_content_review_case_ids)}")
    print(
        "Skipped high-priority mixed review cases: "
        f"{len(summary.skipped_high_priority_review_case_ids)}"
    )

    if summary.duplicate_review_case_ids:
        duplicate_ids = ", ".join(summary.duplicate_review_case_ids)
        print(f"[WARN] Duplicate case_id in review CSV (last row wins): {duplicate_ids}")

    if summary.skipped_high_priority_review_case_ids:
        skipped_ids = ", ".join(summary.skipped_high_priority_review_case_ids)
        print(
            "[WARN] Skipped high-priority mixed review rows; promote split candidates or curate manually: "
            f"{skipped_ids}"
        )

    if args.report:
        report_path = write_merge_report(args.report, summary)
        print(f"Saved merge report to {report_path}")

    if args.dry_run and output_path is None:
        print("Dry run completed. No CSV file written.")

    return 0
