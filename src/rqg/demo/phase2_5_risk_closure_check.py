"""Check monthly residual risk closure controls for Phase2.5."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

WS1_PATH = REPO_ROOT / "docs" / "ops" / "phase2-5-ws1-baseline-sheet.md"
WS2_PATH = REPO_ROOT / "docs" / "ops" / "phase2-5-ws2-failure-review-template.md"

WS1_CUSTOMER_TRACK_HEADER = (
    "| measured_date | operator | customer_repo | onboarding_time_minutes | "
    "weekly_ops_time_minutes | evidence | notes |"
)
WS2_SYNTHETIC_REGRESSION_HEADER = (
    "| executed_date | run_or_pr | scenario | result | evidence | notes |"
)


@dataclass
class RiskClosureSummary:
    lookback_days: int
    reference_date: str
    rc1_customer_track_recent: bool
    rc1_latest_customer_measurement_date: str
    rc2_synthetic_regression_recent: bool
    rc2_latest_synthetic_regression_date: str
    overall_pass: bool
    notes: list[str]


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected ISO date format: YYYY-MM-DD") from exc


def _parse_date(value: str) -> date | None:
    raw = value.strip()
    if not raw or raw == "YYYY-MM-DD":
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _extract_table_rows(path: Path, header_start: str) -> list[list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()

    start_index = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith(header_start):
            start_index = idx
            break

    if start_index < 0:
        return []

    rows: list[list[str]] = []
    for line in lines[start_index + 2 :]:
        if not line.strip().startswith("|"):
            break
        cells = [part.strip() for part in line.split("|")[1:-1]]
        rows.append(cells)
    return rows


def _is_placeholder(cells: list[str]) -> bool:
    joined = " ".join(cells)
    return "YYYY-MM-DD" in joined or "owner-name" in joined


def _check_rc1_customer_track(
    ws1_path: Path,
    *,
    today: date,
    lookback_days: int,
) -> tuple[bool, str, str]:
    rows = _extract_table_rows(ws1_path, WS1_CUSTOMER_TRACK_HEADER)
    real_rows = [row for row in rows if not _is_placeholder(row)]

    latest: date | None = None
    for row in real_rows:
        measured_date = _parse_date(row[0]) if row else None
        if measured_date is None:
            continue
        if latest is None or measured_date > latest:
            latest = measured_date

    if latest is None:
        return False, "", "RC1 missing customer track measurement row"

    threshold = today - timedelta(days=lookback_days)
    if latest < threshold:
        return (
            False,
            latest.isoformat(),
            f"RC1 latest customer track measurement is stale ({latest.isoformat()})",
        )

    return True, latest.isoformat(), "RC1 customer track monthly monitor is fresh"


def _check_rc2_synthetic_regression(
    ws2_path: Path,
    *,
    today: date,
    lookback_days: int,
) -> tuple[bool, str, str]:
    rows = _extract_table_rows(ws2_path, WS2_SYNTHETIC_REGRESSION_HEADER)
    real_rows = [row for row in rows if not _is_placeholder(row)]

    latest_pass: date | None = None
    for row in real_rows:
        executed_date = _parse_date(row[0]) if row else None
        result = row[3].strip().lower() if len(row) > 3 else ""
        if executed_date is None or result != "pass":
            continue
        if latest_pass is None or executed_date > latest_pass:
            latest_pass = executed_date

    if latest_pass is None:
        return False, "", "RC2 missing synthetic regression pass evidence"

    threshold = today - timedelta(days=lookback_days)
    if latest_pass < threshold:
        return (
            False,
            latest_pass.isoformat(),
            f"RC2 latest synthetic regression pass is stale ({latest_pass.isoformat()})",
        )

    return True, latest_pass.isoformat(), "RC2 synthetic regression monthly monitor is fresh"


def collect_summary(
    *,
    ws1_path: Path = WS1_PATH,
    ws2_path: Path = WS2_PATH,
    lookback_days: int = 31,
    today: date | None = None,
) -> RiskClosureSummary:
    if today is None:
        today = datetime.now(UTC).date()

    notes: list[str] = []

    rc1_pass, rc1_latest, rc1_note = _check_rc1_customer_track(
        ws1_path,
        today=today,
        lookback_days=lookback_days,
    )
    notes.append(rc1_note)

    rc2_pass, rc2_latest, rc2_note = _check_rc2_synthetic_regression(
        ws2_path,
        today=today,
        lookback_days=lookback_days,
    )
    notes.append(rc2_note)

    overall_pass = rc1_pass and rc2_pass

    return RiskClosureSummary(
        lookback_days=lookback_days,
        reference_date=today.isoformat(),
        rc1_customer_track_recent=rc1_pass,
        rc1_latest_customer_measurement_date=rc1_latest,
        rc2_synthetic_regression_recent=rc2_pass,
        rc2_latest_synthetic_regression_date=rc2_latest,
        overall_pass=overall_pass,
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check residual risk closure controls for Phase2.5"
    )
    parser.add_argument(
        "--ws1-path",
        default=str(WS1_PATH),
        help="Path to phase2.5 WS1 baseline markdown",
    )
    parser.add_argument(
        "--ws2-path",
        default=str(WS2_PATH),
        help="Path to phase2.5 WS2 failure review markdown",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=31,
        help="Allowed recency window for monthly risk controls",
    )
    parser.add_argument(
        "--reference-date",
        type=_parse_iso_date,
        help="Override reference date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--summary-output",
        help="Optional JSON output path for check summary",
    )
    args = parser.parse_args(argv)

    summary = collect_summary(
        ws1_path=Path(args.ws1_path),
        ws2_path=Path(args.ws2_path),
        lookback_days=args.lookback_days,
        today=args.reference_date,
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
