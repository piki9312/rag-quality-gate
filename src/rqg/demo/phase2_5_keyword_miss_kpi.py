"""Collect keyword_miss false-negative KPI for weekly case-quality operations."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "runs" / "phase2-5-keyword-miss" / "summary.json"


@dataclass
class KeywordMissKpiSummary:
    week_start: str
    run_id: str
    keyword_miss_total: int
    reviewed_total: int
    false_negative_count: int
    false_negative_rate: float | None
    max_false_negative_rate: float
    decision: str
    notes: list[str]


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected ISO date format: YYYY-MM-DD") from exc


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def _collect_keyword_miss_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row for row in rows if str(row.get("failure_type", "")).strip().lower() == "keyword_miss"
    ]


def _load_case_keywords(cases_csv: Path | None) -> dict[str, str]:
    if cases_csv is None:
        return {}

    mapping: dict[str, str] = {}
    with cases_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            case_id = (row.get("case_id") or "").strip()
            if not case_id:
                continue
            mapping[case_id] = (row.get("expected_keywords") or "").strip()
    return mapping


def export_review_template(
    review_csv: Path,
    keyword_miss_rows: list[dict[str, Any]],
    case_keywords: dict[str, str],
) -> None:
    review_csv.parent.mkdir(parents=True, exist_ok=True)
    with review_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "case_id",
                "severity",
                "category",
                "failure_reason",
                "expected_keywords",
                "answer",
                "review_verdict",
                "review_notes",
            ],
        )
        writer.writeheader()
        for row in keyword_miss_rows:
            case_id = str(row.get("case_id") or "").strip()
            writer.writerow(
                {
                    "case_id": case_id,
                    "severity": row.get("severity") or "",
                    "category": row.get("category") or "",
                    "failure_reason": row.get("failure_reason") or "",
                    "expected_keywords": case_keywords.get(case_id, ""),
                    "answer": row.get("answer") or "",
                    "review_verdict": "",
                    "review_notes": "",
                }
            )


def _normalize_review_verdict(raw: str) -> str | None:
    normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return None
    if normalized in {"false_negative", "fn"}:
        return "false_negative"
    if normalized in {"valid_failure", "valid", "true_positive", "tp", "correct_failure"}:
        return "valid_failure"
    return "unknown"


def _collect_review_counts(review_csv: Path) -> tuple[int, int, int]:
    reviewed_total = 0
    false_negative_count = 0
    unknown_verdict_count = 0

    with review_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            verdict = _normalize_review_verdict(row.get("review_verdict") or "")
            if verdict is None:
                continue
            if verdict == "unknown":
                unknown_verdict_count += 1
                continue
            reviewed_total += 1
            if verdict == "false_negative":
                false_negative_count += 1

    return reviewed_total, false_negative_count, unknown_verdict_count


def collect_summary(
    results_jsonl: Path,
    *,
    review_csv: Path | None = None,
    today: date | None = None,
    week_start_override: date | None = None,
    max_false_negative_rate: float = 0.2,
) -> KeywordMissKpiSummary:
    if today is None:
        today = datetime.now(UTC).date()

    if week_start_override is None:
        week_start = (today - timedelta(days=today.weekday())).isoformat()
    else:
        week_start = week_start_override.isoformat()

    rows = _read_jsonl(results_jsonl)
    keyword_miss_rows = _collect_keyword_miss_rows(rows)
    run_id = str(rows[0].get("run_id") or "local") if rows else "local"

    notes: list[str] = [f"keyword_miss_total={len(keyword_miss_rows)}"]
    reviewed_total = 0
    false_negative_count = 0
    false_negative_rate: float | None = None

    if review_csv is not None and review_csv.exists():
        reviewed_total, false_negative_count, unknown_verdict_count = _collect_review_counts(
            review_csv
        )
        if reviewed_total > 0:
            false_negative_rate = round(false_negative_count / reviewed_total, 4)
            notes.append(
                f"reviewed={reviewed_total}, false_negative={false_negative_count}, rate={false_negative_rate:.4f}"
            )
        else:
            notes.append("reviewed=0 (review_verdict not filled)")
        if unknown_verdict_count > 0:
            notes.append(f"unknown_review_verdict={unknown_verdict_count}")
    elif review_csv is not None:
        notes.append(f"review_csv not found: {review_csv}")

    decision = "keep-going"
    if keyword_miss_rows and reviewed_total == 0:
        decision = "investigate"
        notes.append("keyword_miss rows exist but no reviewed verdicts")
    if false_negative_rate is not None and false_negative_rate > max_false_negative_rate:
        decision = "investigate"
        notes.append(
            f"false_negative_rate {false_negative_rate:.4f} exceeds threshold {max_false_negative_rate:.4f}"
        )

    return KeywordMissKpiSummary(
        week_start=week_start,
        run_id=run_id,
        keyword_miss_total=len(keyword_miss_rows),
        reviewed_total=reviewed_total,
        false_negative_count=false_negative_count,
        false_negative_rate=false_negative_rate,
        max_false_negative_rate=max_false_negative_rate,
        decision=decision,
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect keyword_miss false-negative KPI")
    parser.add_argument("--results-jsonl", required=True, help="Path to eval result jsonl")
    parser.add_argument("--cases-csv", help="Optional cases.csv path for expected_keywords lookup")
    parser.add_argument("--review-csv", help="Reviewed CSV path with review_verdict column")
    parser.add_argument(
        "--export-review-csv",
        help="Output path for keyword_miss review template CSV",
    )
    parser.add_argument(
        "--max-false-negative-rate",
        type=float,
        default=0.2,
        help="Threshold to mark investigate when reviewed false-negative rate is high",
    )
    parser.add_argument(
        "--week-start",
        type=_parse_iso_date,
        help="Override week_start (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for KPI summary JSON",
    )
    args = parser.parse_args(argv)

    results_jsonl = Path(args.results_jsonl)
    review_csv = Path(args.review_csv) if args.review_csv else None
    summary = collect_summary(
        results_jsonl,
        review_csv=review_csv,
        week_start_override=args.week_start,
        max_false_negative_rate=args.max_false_negative_rate,
    )

    if args.export_review_csv:
        case_keywords = _load_case_keywords(Path(args.cases_csv) if args.cases_csv else None)
        rows = _collect_keyword_miss_rows(_read_jsonl(results_jsonl))
        export_review_template(Path(args.export_review_csv), rows, case_keywords)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    print(json.dumps(asdict(summary), indent=2))

    if summary.decision == "investigate":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
