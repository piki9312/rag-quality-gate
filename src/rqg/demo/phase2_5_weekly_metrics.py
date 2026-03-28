"""Collect Phase2.5 weekly hardening metrics from WS1/WS2/WS3 records."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

WS1_PATH = REPO_ROOT / "docs" / "ops" / "phase2-5-ws1-baseline-sheet.md"
WS2_PATH = REPO_ROOT / "docs" / "ops" / "phase2-5-ws2-failure-review-template.md"
WS3_PATH = REPO_ROOT / "docs" / "ops" / "phase2-5-ws3-gate-exception-approval-template.md"

DEFAULT_OUTPUT = REPO_ROOT / "runs" / "phase2-5-weekly" / "summary.json"


@dataclass
class WeeklyMetricsSummary:
    week_start: str
    run_id: str
    run_url: str
    onboarding_time_minutes: float
    weekly_ops_time_minutes: float
    failure_action_coverage_rate: float
    gate_exception_count: int
    overdue_exceptions_count: int
    decision: str
    notes: list[str]


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
    return (
        "YYYY-MM-DD" in joined
        or "owner-name" in joined
        or "run id / PR" in joined
        or "EX-YYYYMMDD" in joined
    )


def _to_float(value: str) -> float | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_date(value: str) -> date | None:
    raw = value.strip()
    if not raw or raw == "YYYY-MM-DD":
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _collect_ws1_times() -> tuple[float | None, float | None, str]:
    rows = _extract_table_rows(WS1_PATH, "| measured_date |")
    real_rows = [row for row in rows if not _is_placeholder(row)]
    if not real_rows:
        return None, None, "WS1 baseline row is missing"

    latest = real_rows[-1]
    onboarding = _to_float(latest[5]) if len(latest) > 5 else None
    weekly_ops = _to_float(latest[8]) if len(latest) > 8 else None
    measured_date = latest[0] if latest else "unknown"
    return onboarding, weekly_ops, f"WS1 baseline measured_date={measured_date}"


def _collect_ws2_coverage() -> tuple[float, str]:
    rows = _extract_table_rows(WS2_PATH, "| week_start |")
    real_rows = [row for row in rows if not _is_placeholder(row)]
    fail_total = len(real_rows)
    if fail_total == 0:
        return 1.0, "WS2 no failure rows this week"

    covered = 0
    for row in real_rows:
        action_owner = row[5].strip() if len(row) > 5 else ""
        due_date = row[6].strip() if len(row) > 6 else ""
        if action_owner and due_date and due_date != "YYYY-MM-DD":
            covered += 1

    rate = covered / fail_total
    return rate, f"WS2 covered={covered}/{fail_total}"


def _collect_ws3_exception_counts(today: date) -> tuple[int, int, str]:
    rows = _extract_table_rows(WS3_PATH, "| request_id |")
    real_rows = [row for row in rows if not _is_placeholder(row)]

    active = 0
    overdue = 0
    for row in real_rows:
        status = row[9].strip().lower() if len(row) > 9 else ""
        expires_at = _parse_date(row[8]) if len(row) > 8 else None
        if status == "active":
            active += 1
            if expires_at is not None and expires_at < today:
                overdue += 1

    return active, overdue, f"WS3 active={active}, overdue={overdue}"


def _build_run_metadata() -> tuple[str, str]:
    run_id = os.getenv("GITHUB_RUN_ID", "local")
    server = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if repo and run_id != "local":
        run_url = f"{server}/{repo}/actions/runs/{run_id}"
    else:
        run_url = ""
    return run_id, run_url


def collect_summary(today: date | None = None) -> WeeklyMetricsSummary:
    if today is None:
        today = datetime.now(UTC).date()

    week_start = (today - timedelta(days=today.weekday())).isoformat()
    run_id, run_url = _build_run_metadata()

    notes: list[str] = []

    onboarding, weekly_ops, ws1_note = _collect_ws1_times()
    notes.append(ws1_note)

    coverage_rate, ws2_note = _collect_ws2_coverage()
    notes.append(ws2_note)

    gate_exception_count, overdue_exceptions_count, ws3_note = _collect_ws3_exception_counts(today)
    notes.append(ws3_note)

    decision = "keep-going"

    if onboarding is None:
        decision = "investigate"
        notes.append("M1 onboarding_time_minutes is missing")
    if weekly_ops is None:
        decision = "investigate"
        notes.append("M2 weekly_ops_time_minutes is missing")
    if coverage_rate < 1.0:
        decision = "investigate"
        notes.append("M3 failure_action_coverage_rate is below 1.0")
    if overdue_exceptions_count > 0:
        decision = "investigate"
        notes.append("M5 overdue_exceptions_count is greater than 0")

    return WeeklyMetricsSummary(
        week_start=week_start,
        run_id=run_id,
        run_url=run_url,
        onboarding_time_minutes=round(onboarding or 0.0, 2),
        weekly_ops_time_minutes=round(weekly_ops or 0.0, 2),
        failure_action_coverage_rate=round(coverage_rate, 4),
        gate_exception_count=gate_exception_count,
        overdue_exceptions_count=overdue_exceptions_count,
        decision=decision,
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Phase2.5 weekly hardening metrics")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for summary JSON",
    )
    args = parser.parse_args(argv)

    summary = collect_summary()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")

    print(json.dumps(asdict(summary), indent=2))

    if summary.decision == "investigate":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
