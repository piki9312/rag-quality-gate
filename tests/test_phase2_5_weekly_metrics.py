from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from rqg.demo import phase2_5_weekly_metrics as metrics


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _ws1_markdown(with_real_row: bool = True) -> str:
    base = """
# WS1

| measured_date | operator | sample_repo | onboarding_start | onboarding_end | onboarding_time_minutes | weekly_ops_start | weekly_ops_end | weekly_ops_time_minutes | evidence | notes |
| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | --- | --- |
| YYYY-MM-DD | owner-name | packs/hr | YYYY-MM-DD hh:mm | YYYY-MM-DD hh:mm | 0 | YYYY-MM-DD hh:mm | YYYY-MM-DD hh:mm | 0 | run URL / log path | condition notes |
""".lstrip()
    if not with_real_row:
        return base
    return (
        base
        + "| 2026-03-28 | piki9312 | packs/hr | 2026-03-28 11:48 | 2026-03-28 11:48 | 0.25 | 2026-03-28 02:45 (UTC) | 2026-03-28 02:47 (UTC) | 1.57 | summary.json | note |\n"
    )


def _ws2_markdown(real_rows: list[str] | None = None) -> str:
    body = """
# WS2

| week_start | run_or_pr | failure_category | incident_summary | root_cause_hypothesis | action_owner | due_date | action_status | verified_next_week | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | run id / PR | retrieval_miss | short summary | hypothesis | owner | YYYY-MM-DD | open / in-progress / done | yes / no | memo |
""".lstrip()
    for row in real_rows or []:
        body += row + "\n"
    return body


def _ws3_markdown(real_rows: list[str] | None = None) -> str:
    body = """
# WS3

| request_id | requested_date | category | affected_scope | reason | requested_by | approver | approved_date | expires_at | status | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EX-YYYYMMDD-001 | YYYY-MM-DD | warn_only_override / no_data_temporary / manual_override | repo/path, workflow, case source | short reason | owner | approver | YYYY-MM-DD | YYYY-MM-DD | active / expired / revoked | issue/pr/run URL |
""".lstrip()
    for row in real_rows or []:
        body += row + "\n"
    return body


@pytest.fixture
def metrics_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    ws1 = tmp_path / "ws1.md"
    ws2 = tmp_path / "ws2.md"
    ws3 = tmp_path / "ws3.md"

    monkeypatch.setattr(metrics, "WS1_PATH", ws1)
    monkeypatch.setattr(metrics, "WS2_PATH", ws2)
    monkeypatch.setattr(metrics, "WS3_PATH", ws3)

    return ws1, ws2, ws3


def test_collect_summary_keep_going(
    metrics_docs: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    ws1, ws2, ws3 = metrics_docs
    _write(ws1, _ws1_markdown(with_real_row=True))
    _write(ws2, _ws2_markdown(real_rows=[]))
    _write(ws3, _ws3_markdown(real_rows=[]))

    monkeypatch.setenv("GITHUB_RUN_ID", "123456")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

    summary = metrics.collect_summary(today=date(2026, 3, 28))

    assert summary.week_start == "2026-03-23"
    assert summary.run_id == "123456"
    assert summary.run_url == "https://github.com/owner/repo/actions/runs/123456"
    assert summary.onboarding_time_minutes == 0.25
    assert summary.weekly_ops_time_minutes == 1.57
    assert summary.failure_action_coverage_rate == 1.0
    assert summary.gate_exception_count == 0
    assert summary.overdue_exceptions_count == 0
    assert summary.decision == "keep-going"


def test_collect_summary_with_week_start_override(
    metrics_docs: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws1, ws2, ws3 = metrics_docs
    _write(ws1, _ws1_markdown(with_real_row=True))
    _write(ws2, _ws2_markdown(real_rows=[]))
    _write(ws3, _ws3_markdown(real_rows=[]))

    monkeypatch.setenv("GITHUB_RUN_ID", "654321")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

    summary = metrics.collect_summary(
        today=date(2026, 3, 28),
        week_start_override=date(2026, 3, 16),
    )

    assert summary.week_start == "2026-03-16"
    assert summary.run_id == "654321"
    assert any("week_start_override=2026-03-16" in note for note in summary.notes)


def test_collect_summary_investigate(metrics_docs: tuple[Path, Path, Path]) -> None:
    ws1, ws2, ws3 = metrics_docs
    _write(ws1, _ws1_markdown(with_real_row=False))
    _write(
        ws2,
        _ws2_markdown(
            real_rows=[
                "| 2026-03-24 | PR-18 | retrieval_miss | miss | root |  |  | open | no | uncovered |",
                "| 2026-03-24 | PR-19 | stale_source | stale | root | alice | 2026-03-29 | in-progress | no | covered |",
            ]
        ),
    )
    _write(
        ws3,
        _ws3_markdown(
            real_rows=[
                "| EX-20260324-001 | 2026-03-24 | manual_override | packs/hr | reason | bob | owner | 2026-03-24 | 2026-03-27 | active | https://example.com |"
            ]
        ),
    )

    summary = metrics.collect_summary(today=date(2026, 3, 28))

    assert summary.onboarding_time_minutes == 0.0
    assert summary.weekly_ops_time_minutes == 0.0
    assert summary.failure_action_coverage_rate == 0.5
    assert summary.gate_exception_count == 1
    assert summary.overdue_exceptions_count == 1
    assert summary.decision == "investigate"
    assert any("M1 onboarding_time_minutes is missing" in note for note in summary.notes)
    assert any("M2 weekly_ops_time_minutes is missing" in note for note in summary.notes)
    assert any("M3 failure_action_coverage_rate is below 1.0" in note for note in summary.notes)
    assert any("M5 overdue_exceptions_count is greater than 0" in note for note in summary.notes)


def test_main_writes_output_and_returns_exit_codes(
    metrics_docs: tuple[Path, Path, Path],
    tmp_path: Path,
) -> None:
    ws1, ws2, ws3 = metrics_docs
    out = tmp_path / "summary.json"

    _write(ws1, _ws1_markdown(with_real_row=True))
    _write(ws2, _ws2_markdown(real_rows=[]))
    _write(ws3, _ws3_markdown(real_rows=[]))

    ok_exit = metrics.main(["--output", str(out)])
    assert ok_exit == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["decision"] == "keep-going"

    backfill_exit = metrics.main(["--output", str(out), "--week-start", "2026-03-16"])
    assert backfill_exit == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["week_start"] == "2026-03-16"

    _write(ws1, _ws1_markdown(with_real_row=False))
    fail_exit = metrics.main(["--output", str(out)])
    assert fail_exit == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["decision"] == "investigate"


def test_render_register_row_formats_values(
    metrics_docs: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws1, ws2, ws3 = metrics_docs
    _write(ws1, _ws1_markdown(with_real_row=True))
    _write(ws2, _ws2_markdown(real_rows=[]))
    _write(ws3, _ws3_markdown(real_rows=[]))

    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)

    summary = metrics.collect_summary(today=date(2026, 3, 28))
    row = metrics.render_register_row(summary, "piki9312")

    assert row.startswith("| 2026-03-23 | local |")
    assert "| 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | piki9312 |" in row


def test_append_register_row_is_idempotent(tmp_path: Path) -> None:
    register = tmp_path / "register.md"
    register.write_text(
        "# Register\n\n## Current records\n\n| h |\n| - |\n\n## Update procedure\n1. step\n",
        encoding="utf-8",
    )
    row = "| 2026-03-23 | 111 | https://example.com | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | note |"

    first = metrics.append_register_row(register, row, "111")
    second = metrics.append_register_row(register, row, "111")

    content = register.read_text(encoding="utf-8")
    assert first is True
    assert second is False
    assert content.count("| 2026-03-23 | 111 |") == 1


def test_main_append_register_writes_row(
    metrics_docs: tuple[Path, Path, Path],
    tmp_path: Path,
) -> None:
    ws1, ws2, ws3 = metrics_docs
    _write(ws1, _ws1_markdown(with_real_row=True))
    _write(ws2, _ws2_markdown(real_rows=[]))
    _write(ws3, _ws3_markdown(real_rows=[]))

    out = tmp_path / "summary.json"
    register = tmp_path / "register.md"
    register.write_text(
        "# Register\n\n## Current records\n\n| h |\n| - |\n\n## Update procedure\n1. step\n",
        encoding="utf-8",
    )

    exit_code = metrics.main(
        [
            "--output",
            str(out),
            "--append-register",
            "--register-path",
            str(register),
            "--reviewer",
            "piki9312",
        ]
    )

    assert exit_code == 0
    content = register.read_text(encoding="utf-8")
    assert "| keep-going | piki9312 |" in content


def test_extract_table_rows_returns_empty_when_header_not_found(tmp_path: Path) -> None:
    path = tmp_path / "table.md"
    _write(path, "# no table here\n")
    assert metrics._extract_table_rows(path, "| week_start |") == []
