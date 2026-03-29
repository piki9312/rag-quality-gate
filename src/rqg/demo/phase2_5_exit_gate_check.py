"""Evaluate fixed C1-C4 provisional exit decision rules for Phase2.5."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

REGISTER_PATH = REPO_ROOT / "docs" / "ops" / "phase2-5-weekly-metrics-register.md"
CASE_QUALITY_WEEKLY_REVIEW_PATH = (
    REPO_ROOT / "docs" / "ops" / "phase2-5-case-quality-weekly-review.md"
)
PACK_CASES_GLOB = "packs/*/cases.csv"


@dataclass
class WeekEvidenceCheck:
    week_start: str
    row_count: int
    evidence_pass: bool
    selected_run_id: str
    selected_run_url: str
    coverage_rate: float | None
    overdue_exceptions_count: int | None
    decision: str
    note: str


@dataclass
class ExitGateCheckSummary:
    required_weeks: int
    coverage_threshold: float
    evaluated_week_starts: list[str]
    c1_four_week_evidence_continuity: bool
    c2_overdue_exceptions_zero: bool
    c3_stale_timestamp_risk_resolved: bool
    c4_failure_action_coverage_threshold: bool
    overall_pass: bool
    stale_rule_present: bool
    packs_checked: list[str]
    packs_missing_timestamp_column: list[str]
    week_checks: list[WeekEvidenceCheck]
    notes: list[str]


def _to_float(value: str) -> float | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _to_int(value: str) -> int | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _to_date(value: str) -> date | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _extract_current_record_rows(register_path: Path) -> list[list[str]]:
    lines = register_path.read_text(encoding="utf-8").splitlines()

    current_records_idx = -1
    for idx, line in enumerate(lines):
        if line.strip() == "## Current records":
            current_records_idx = idx
            break

    if current_records_idx < 0:
        raise ValueError("Register file does not contain '## Current records' section")

    header_idx = -1
    for idx in range(current_records_idx + 1, len(lines)):
        if lines[idx].strip().startswith("| week_start | run_id | run_url |"):
            header_idx = idx
            break

    if header_idx < 0:
        raise ValueError("Register file does not contain current records table header")

    rows: list[list[str]] = []
    for line in lines[header_idx + 2 :]:
        if not line.strip().startswith("|"):
            break
        cells = [part.strip() for part in line.split("|")[1:-1]]
        if not cells:
            continue
        if cells[0] == "YYYY-MM-DD":
            continue
        rows.append(cells)
    return rows


def _resolve_pack_case_paths(explicit_paths: list[Path] | None) -> list[Path]:
    if explicit_paths is not None:
        return sorted(explicit_paths)
    return sorted(REPO_ROOT.glob(PACK_CASES_GLOB))


def _check_stale_timestamp_risk(
    case_quality_weekly_review_path: Path,
    pack_case_paths: list[Path],
) -> tuple[bool, list[str], list[str], bool]:
    review_text = case_quality_weekly_review_path.read_text(encoding="utf-8")
    stale_rule_present = "today - last_reviewed_at > 30 days" in review_text

    packs_checked: list[str] = []
    packs_missing_timestamp_column: list[str] = []

    for case_file in pack_case_paths:
        try:
            rel_path = str(case_file.relative_to(REPO_ROOT)).replace("\\", "/")
        except ValueError:
            rel_path = str(case_file).replace("\\", "/")

        packs_checked.append(rel_path)

        with open(case_file, "r", encoding="utf-8", newline="") as file_obj:
            reader = csv.reader(file_obj)
            header = next(reader, [])

        normalized_header = [col.strip().lstrip("\ufeff") for col in header]
        if "last_reviewed_at" not in normalized_header:
            packs_missing_timestamp_column.append(rel_path)

    c3_pass = stale_rule_present and bool(pack_case_paths) and not packs_missing_timestamp_column
    return c3_pass, packs_checked, packs_missing_timestamp_column, stale_rule_present


def collect_gate_summary(
    *,
    register_path: Path = REGISTER_PATH,
    case_quality_weekly_review_path: Path = CASE_QUALITY_WEEKLY_REVIEW_PATH,
    pack_case_paths: list[Path] | None = None,
    required_weeks: int = 4,
    coverage_threshold: float = 1.0,
) -> ExitGateCheckSummary:
    rows = _extract_current_record_rows(register_path)
    notes: list[str] = []

    week_rows: dict[date, list[dict[str, object]]] = {}
    for cells in rows:
        if len(cells) < 11:
            cells = cells + [""] * (11 - len(cells))

        week_start = cells[0]
        week_date = _to_date(week_start)
        if week_date is None:
            notes.append(f"skipped invalid week_start row: {week_start}")
            continue

        run_id = cells[1].strip()
        run_url = cells[2].strip()
        coverage_rate = _to_float(cells[5])
        overdue_exceptions_count = _to_int(cells[7])
        decision = cells[8].strip()

        row_trace_ok = bool(run_id and run_url)
        row_metrics_ok = all(
            [
                _to_float(cells[3]) is not None,
                _to_float(cells[4]) is not None,
                coverage_rate is not None,
                _to_int(cells[6]) is not None,
                overdue_exceptions_count is not None,
                bool(decision),
            ]
        )
        row_threshold_ok = bool(
            decision == "keep-going"
            and coverage_rate is not None
            and coverage_rate >= coverage_threshold
            and overdue_exceptions_count == 0
        )

        week_rows.setdefault(week_date, []).append(
            {
                "run_id": run_id,
                "run_url": run_url,
                "coverage_rate": coverage_rate,
                "overdue_exceptions_count": overdue_exceptions_count,
                "decision": decision,
                "trace_ok": row_trace_ok,
                "metrics_ok": row_metrics_ok,
                "threshold_ok": row_threshold_ok,
            }
        )

    sorted_weeks = sorted(week_rows.keys(), reverse=True)
    target_weeks = sorted_weeks[:required_weeks]

    week_checks: list[WeekEvidenceCheck] = []
    for week in target_weeks:
        candidates = week_rows[week]
        selected = next(
            (
                item
                for item in candidates
                if bool(item["trace_ok"])
                and bool(item["metrics_ok"])
                and bool(item["threshold_ok"])
            ),
            None,
        )

        if selected is not None:
            week_checks.append(
                WeekEvidenceCheck(
                    week_start=week.isoformat(),
                    row_count=len(candidates),
                    evidence_pass=True,
                    selected_run_id=str(selected["run_id"]),
                    selected_run_url=str(selected["run_url"]),
                    coverage_rate=(
                        selected["coverage_rate"]
                        if isinstance(selected["coverage_rate"], float)
                        else None
                    ),
                    overdue_exceptions_count=(
                        selected["overdue_exceptions_count"]
                        if isinstance(selected["overdue_exceptions_count"], int)
                        else None
                    ),
                    decision=str(selected["decision"]),
                    note="",
                )
            )
            continue

        week_checks.append(
            WeekEvidenceCheck(
                week_start=week.isoformat(),
                row_count=len(candidates),
                evidence_pass=False,
                selected_run_id="",
                selected_run_url="",
                coverage_rate=None,
                overdue_exceptions_count=None,
                decision="",
                note="No row satisfies E2+E3+E4 simultaneously",
            )
        )

    has_required_weeks = len(target_weeks) == required_weeks
    if not has_required_weeks:
        notes.append(
            f"insufficient weeks: expected {required_weeks}, found {len(target_weeks)} unique week_start"
        )

    is_consecutive = has_required_weeks and all(
        0 < (target_weeks[idx] - target_weeks[idx + 1]).days <= 7
        for idx in range(len(target_weeks) - 1)
    )
    if has_required_weeks and not is_consecutive:
        notes.append("latest required week_start values are not consecutive")

    c1_pass = (
        has_required_weeks and is_consecutive and all(item.evidence_pass for item in week_checks)
    )
    c2_pass = has_required_weeks and all(
        item.evidence_pass and item.overdue_exceptions_count == 0 for item in week_checks
    )
    c4_pass = has_required_weeks and all(
        item.evidence_pass
        and item.coverage_rate is not None
        and item.coverage_rate >= coverage_threshold
        for item in week_checks
    )

    resolved_pack_paths = _resolve_pack_case_paths(pack_case_paths)
    c3_pass, packs_checked, packs_missing, stale_rule_present = _check_stale_timestamp_risk(
        case_quality_weekly_review_path=case_quality_weekly_review_path,
        pack_case_paths=resolved_pack_paths,
    )

    if not c3_pass and not stale_rule_present:
        notes.append("stale rule expression is missing in case quality weekly review doc")
    if not c3_pass and packs_missing:
        notes.append("last_reviewed_at column is missing in one or more packs/*/cases.csv")
    if not c3_pass and not resolved_pack_paths:
        notes.append("no packs/*/cases.csv files were found")

    overall_pass = c1_pass and c2_pass and c3_pass and c4_pass

    return ExitGateCheckSummary(
        required_weeks=required_weeks,
        coverage_threshold=coverage_threshold,
        evaluated_week_starts=[item.week_start for item in week_checks],
        c1_four_week_evidence_continuity=c1_pass,
        c2_overdue_exceptions_zero=c2_pass,
        c3_stale_timestamp_risk_resolved=c3_pass,
        c4_failure_action_coverage_threshold=c4_pass,
        overall_pass=overall_pass,
        stale_rule_present=stale_rule_present,
        packs_checked=packs_checked,
        packs_missing_timestamp_column=packs_missing,
        week_checks=week_checks,
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check fixed C1-C4 provisional exit decision rules"
    )
    parser.add_argument(
        "--register-path",
        default=str(REGISTER_PATH),
        help="Path to phase2.5 weekly metrics register markdown",
    )
    parser.add_argument(
        "--case-quality-weekly-review-path",
        default=str(CASE_QUALITY_WEEKLY_REVIEW_PATH),
        help="Path to phase2.5 case quality weekly review markdown",
    )
    parser.add_argument(
        "--required-weeks",
        type=int,
        default=4,
        help="Required consecutive week count for C1",
    )
    parser.add_argument(
        "--coverage-threshold",
        type=float,
        default=1.0,
        help="Minimum failure_action_coverage_rate required for C4",
    )
    parser.add_argument(
        "--summary-output",
        help="Optional JSON output path for check summary",
    )
    args = parser.parse_args(argv)

    summary = collect_gate_summary(
        register_path=Path(args.register_path),
        case_quality_weekly_review_path=Path(args.case_quality_weekly_review_path),
        required_weeks=args.required_weeks,
        coverage_threshold=args.coverage_threshold,
    )

    payload = asdict(summary)
    print(json.dumps(payload, indent=2))

    if args.summary_output:
        output_path = Path(args.summary_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return 0 if summary.overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
