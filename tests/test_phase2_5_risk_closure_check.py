from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from rqg.demo import phase2_5_risk_closure_check as risk_check


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _ws1_with_customer_track(rows: list[str] | None = None) -> str:
    body = """
# WS1 baseline

## Customer Repo Track Log

| measured_date | operator | customer_repo | onboarding_time_minutes | weekly_ops_time_minutes | evidence | notes |
| --- | --- | --- | ---: | ---: | --- | --- |
| YYYY-MM-DD | owner-name | org/repo | 0.00 | 0.00 | run URL / log path | monthly customer track evidence |
""".lstrip()
    for row in rows or []:
        body += row + "\n"
    return body


def _ws2_with_synthetic_log(rows: list[str] | None = None) -> str:
    body = """
# WS2 failure review

## Synthetic Regression Monthly Log

| executed_date | run_or_pr | scenario | result | evidence | notes |
| --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | run id / PR | scenario-name | pass / fail | run URL / report path | monthly synthetic regression evidence |
""".lstrip()
    for row in rows or []:
        body += row + "\n"
    return body


@pytest.fixture
def risk_docs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    ws1 = tmp_path / "ws1.md"
    ws2 = tmp_path / "ws2.md"

    monkeypatch.setattr(risk_check, "WS1_PATH", ws1)
    monkeypatch.setattr(risk_check, "WS2_PATH", ws2)

    return ws1, ws2


def test_collect_summary_passes_with_recent_customer_and_synthetic_rows(
    risk_docs: tuple[Path, Path],
) -> None:
    ws1, ws2 = risk_docs
    _write(
        ws1,
        _ws1_with_customer_track(
            rows=[
                "| 2026-03-29 | piki9312 | piki9312/rag-quality-gate | 0.25 | 1.57 | https://example.com/ws1 | customer track pilot |"
            ]
        ),
    )
    _write(
        ws2,
        _ws2_with_synthetic_log(
            rows=[
                "| 2026-03-29 | run 23701830709 | legacy migration baseline | pass | https://example.com/ws2 | monthly synthetic regression |"
            ]
        ),
    )

    summary = risk_check.collect_summary(
        ws1_path=ws1,
        ws2_path=ws2,
        today=date(2026, 3, 29),
        lookback_days=31,
    )

    assert summary.rc1_customer_track_recent is True
    assert summary.rc1_latest_customer_measurement_date == "2026-03-29"
    assert summary.rc2_synthetic_regression_recent is True
    assert summary.rc2_latest_synthetic_regression_date == "2026-03-29"
    assert summary.overall_pass is True


def test_collect_summary_fails_when_customer_track_row_is_missing(
    risk_docs: tuple[Path, Path],
) -> None:
    ws1, ws2 = risk_docs
    _write(ws1, _ws1_with_customer_track(rows=[]))
    _write(
        ws2,
        _ws2_with_synthetic_log(
            rows=[
                "| 2026-03-29 | run 23701830709 | legacy migration baseline | pass | https://example.com/ws2 | monthly synthetic regression |"
            ]
        ),
    )

    summary = risk_check.collect_summary(
        ws1_path=ws1,
        ws2_path=ws2,
        today=date(2026, 3, 29),
        lookback_days=31,
    )

    assert summary.rc1_customer_track_recent is False
    assert summary.rc1_latest_customer_measurement_date == ""
    assert summary.overall_pass is False
    assert any("RC1 missing customer track" in note for note in summary.notes)


def test_collect_summary_fails_when_synthetic_regression_is_stale(
    risk_docs: tuple[Path, Path],
) -> None:
    ws1, ws2 = risk_docs
    _write(
        ws1,
        _ws1_with_customer_track(
            rows=[
                "| 2026-03-29 | piki9312 | piki9312/rag-quality-gate | 0.25 | 1.57 | https://example.com/ws1 | customer track pilot |"
            ]
        ),
    )
    _write(
        ws2,
        _ws2_with_synthetic_log(
            rows=[
                "| 2026-01-10 | run 100 | legacy migration baseline | pass | https://example.com/ws2 | old evidence |"
            ]
        ),
    )

    summary = risk_check.collect_summary(
        ws1_path=ws1,
        ws2_path=ws2,
        today=date(2026, 3, 29),
        lookback_days=31,
    )

    assert summary.rc1_customer_track_recent is True
    assert summary.rc2_synthetic_regression_recent is False
    assert summary.rc2_latest_synthetic_regression_date == "2026-01-10"
    assert summary.overall_pass is False
    assert any("RC2 latest synthetic regression pass is stale" in note for note in summary.notes)


def test_main_writes_summary_and_returns_exit_code(
    risk_docs: tuple[Path, Path],
    tmp_path: Path,
) -> None:
    ws1, ws2 = risk_docs
    _write(
        ws1,
        _ws1_with_customer_track(
            rows=[
                "| 2026-03-29 | piki9312 | piki9312/rag-quality-gate | 0.25 | 1.57 | https://example.com/ws1 | customer track pilot |"
            ]
        ),
    )
    _write(
        ws2,
        _ws2_with_synthetic_log(
            rows=[
                "| 2026-03-29 | run 23701830709 | legacy migration baseline | pass | https://example.com/ws2 | monthly synthetic regression |"
            ]
        ),
    )

    output = tmp_path / "risk_summary.json"
    exit_code = risk_check.main(
        [
            "--ws1-path",
            str(ws1),
            "--ws2-path",
            str(ws2),
            "--reference-date",
            "2026-03-29",
            "--summary-output",
            str(output),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["overall_pass"] is True
