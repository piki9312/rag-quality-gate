"""Collect Phase2.5 weekly hardening metrics from WS1/WS2/WS3 records."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

WS1_PATH = REPO_ROOT / "docs" / "ops" / "phase2-5-ws1-baseline-sheet.md"
WS2_PATH = REPO_ROOT / "docs" / "ops" / "phase2-5-ws2-failure-review-template.md"
WS3_PATH = REPO_ROOT / "docs" / "ops" / "phase2-5-ws3-gate-exception-approval-template.md"
REGISTER_PATH = REPO_ROOT / "docs" / "ops" / "phase2-5-weekly-metrics-register.md"

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
    notes: list[str] = field(default_factory=list)
    next_actions: list[WeeklyNextAction] = field(default_factory=list)
    non_technical_summary: list[str] = field(default_factory=list)


@dataclass
class WeeklyNextAction:
    failure_category: str
    run_or_pr: str
    incident_summary: str
    owner: str
    due_date: str
    status: str
    recommended_action: str


def render_register_row(summary: WeeklyMetricsSummary, reviewer: str) -> str:
    notes_text = ", ".join(summary.notes)
    return (
        f"| {summary.week_start} | {summary.run_id} | {summary.run_url} | "
        f"{summary.onboarding_time_minutes:.2f} | {summary.weekly_ops_time_minutes:.2f} | "
        f"{summary.failure_action_coverage_rate:.2f} | {summary.gate_exception_count} | "
        f"{summary.overdue_exceptions_count} | {summary.decision} | {reviewer} | {notes_text} |"
    )


def append_register_row(register_path: Path, row: str, run_id: str) -> bool:
    content = register_path.read_text(encoding="utf-8")
    if f"| {run_id} |" in content:
        return False

    marker = "## Update procedure"
    idx = content.find(marker)
    if idx < 0:
        raise ValueError("Register file does not contain '## Update procedure' section")

    head = content[:idx].rstrip()
    tail = content[idx:]
    new_content = f"{head}\n{row}\n\n{tail}"
    register_path.write_text(new_content, encoding="utf-8")
    return True


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


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Expected ISO date format: YYYY-MM-DD") from exc


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


def _is_in_summary_week(row: list[str], week_start: str) -> bool:
    row_week_start = row[0].strip() if len(row) > 0 else ""
    row_week_start_date = _parse_date(row_week_start)
    summary_week_start = _parse_date(week_start)

    if summary_week_start is not None and row_week_start_date is not None:
        days_offset = (row_week_start_date - summary_week_start).days
        return 0 <= days_offset <= 6

    return row_week_start == week_start


def _collect_ws2_coverage(week_start: str) -> tuple[float, str]:
    rows = _extract_table_rows(WS2_PATH, "| week_start |")
    real_rows = [row for row in rows if not _is_placeholder(row)]
    week_rows = [row for row in real_rows if _is_in_summary_week(row, week_start)]
    fail_total = len(week_rows)
    if fail_total == 0:
        return 1.0, f"WS2 no failure rows for week_start={week_start}"

    covered = 0
    for row in week_rows:
        action_owner = row[5].strip() if len(row) > 5 else ""
        due_date = row[6].strip() if len(row) > 6 else ""
        if action_owner and due_date and due_date != "YYYY-MM-DD":
            covered += 1

    rate = covered / fail_total
    return rate, f"WS2 covered={covered}/{fail_total} (week_start={week_start})"


def _load_ws2_recommended_actions() -> dict[str, str]:
    rows = _extract_table_rows(WS2_PATH, "| failure_category |")
    recommended_actions: dict[str, str] = {}

    for row in rows:
        category = row[0].strip() if len(row) > 0 else ""
        first_action = row[1].strip() if len(row) > 1 else ""
        if not category or not first_action:
            continue
        if category == "failure_category":
            continue
        recommended_actions[category] = first_action

    return recommended_actions


def _collect_ws2_next_actions(week_start: str) -> tuple[list[WeeklyNextAction], str]:
    rows = _extract_table_rows(WS2_PATH, "| week_start |")
    real_rows = [row for row in rows if not _is_placeholder(row)]
    recommended_actions = _load_ws2_recommended_actions()

    next_actions: list[WeeklyNextAction] = []
    for row in real_rows:
        if not _is_in_summary_week(row, week_start):
            continue

        category = row[2].strip() if len(row) > 2 else "other"
        if not category:
            category = "other"

        run_or_pr = row[1].strip() if len(row) > 1 else "n/a"
        incident_summary = row[3].strip() if len(row) > 3 else ""
        owner = row[5].strip() if len(row) > 5 else ""
        due_date = row[6].strip() if len(row) > 6 else ""
        status = row[7].strip() if len(row) > 7 else ""

        owner = owner or "T.B.D."
        due_date = due_date or "T.B.D."
        status = status or "open"

        recommended_action = recommended_actions.get(
            category,
            "Define next action in weekly review issue",
        )

        next_actions.append(
            WeeklyNextAction(
                failure_category=category,
                run_or_pr=run_or_pr,
                incident_summary=incident_summary,
                owner=owner,
                due_date=due_date,
                status=status,
                recommended_action=recommended_action,
            )
        )

    if not next_actions:
        return [], f"WS2 next_actions for week_start={week_start}: none"

    return next_actions, f"WS2 next_actions for week_start={week_start}: {len(next_actions)}"


def _build_non_technical_summary(
    *,
    decision: str,
    coverage_rate: float,
    gate_exception_count: int,
    overdue_exceptions_count: int,
    next_actions: list[WeeklyNextAction],
) -> list[str]:
    decision_message = "Quality gate stayed within agreed limits."
    if decision == "investigate":
        decision_message = "Quality gate needs follow-up actions before next release decision."

    summary = [
        f"Weekly decision: {decision}. {decision_message}",
        f"Failure-to-action coverage: {coverage_rate * 100:.1f}% (target 100.0%).",
        f"Active exceptions: {gate_exception_count}; overdue exceptions: {overdue_exceptions_count}.",
    ]

    if not next_actions:
        summary.append("No WS2 failure rows were recorded for this week.")
        return summary

    open_actions = [
        action
        for action in next_actions
        if action.status.strip().lower() in {"open", "in-progress"}
    ]
    if not open_actions:
        summary.append("All recorded WS2 actions are marked done.")
        return summary

    summary.append(f"Open follow-up actions this week: {len(open_actions)}.")
    for action in open_actions[:3]:
        summary.append(
            "Priority action: "
            f"{action.failure_category} -> {action.recommended_action} "
            f"(owner: {action.owner}, due: {action.due_date})."
        )

    return summary


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


def collect_summary(
    today: date | None = None,
    *,
    week_start_override: date | None = None,
) -> WeeklyMetricsSummary:
    if today is None:
        today = datetime.now(UTC).date()

    if week_start_override is None:
        week_start = (today - timedelta(days=today.weekday())).isoformat()
    else:
        week_start = week_start_override.isoformat()

    run_id, run_url = _build_run_metadata()

    notes: list[str] = []

    onboarding, weekly_ops, ws1_note = _collect_ws1_times()
    notes.append(ws1_note)

    coverage_rate, ws2_note = _collect_ws2_coverage(week_start)
    notes.append(ws2_note)

    next_actions, ws2_actions_note = _collect_ws2_next_actions(week_start)
    notes.append(ws2_actions_note)

    gate_exception_count, overdue_exceptions_count, ws3_note = _collect_ws3_exception_counts(today)
    notes.append(ws3_note)

    if week_start_override is not None:
        notes.append(f"week_start_override={week_start}")

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

    non_technical_summary = _build_non_technical_summary(
        decision=decision,
        coverage_rate=coverage_rate,
        gate_exception_count=gate_exception_count,
        overdue_exceptions_count=overdue_exceptions_count,
        next_actions=next_actions,
    )

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
        next_actions=next_actions,
        non_technical_summary=non_technical_summary,
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Phase2.5 weekly hardening metrics")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for summary JSON",
    )
    parser.add_argument(
        "--print-register-row",
        action="store_true",
        help="Print markdown row for phase2.5 weekly metrics register",
    )
    parser.add_argument(
        "--append-register",
        action="store_true",
        help="Append markdown row to phase2.5 weekly metrics register",
    )
    parser.add_argument(
        "--register-path",
        default=str(REGISTER_PATH),
        help="Path to phase2.5 weekly metrics register markdown file",
    )
    parser.add_argument(
        "--reviewer",
        default=os.getenv("GITHUB_ACTOR", "owner-name"),
        help="Reviewer name written to the register row",
    )
    parser.add_argument(
        "--week-start",
        type=_parse_iso_date,
        help="Override week_start in summary/register row (YYYY-MM-DD)",
    )
    args = parser.parse_args(argv)

    summary = collect_summary(week_start_override=args.week_start)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")

    print(json.dumps(asdict(summary), indent=2))

    row = render_register_row(summary, args.reviewer)
    if args.print_register_row:
        print(row)

    if args.append_register:
        register_path = Path(args.register_path)
        appended = append_register_row(register_path, row, summary.run_id)
        if appended:
            print(f"appended register row to {register_path}")
        else:
            print(f"register row already exists for run_id={summary.run_id}")

    if summary.decision == "investigate":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
