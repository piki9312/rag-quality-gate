from __future__ import annotations

from pathlib import Path

from rqg.demo import phase2_5_exit_gate_check as gate_check


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _register(rows: list[str]) -> str:
    body = """
# Register

## Current records

| week_start | run_id | run_url | onboarding_time_minutes | weekly_ops_time_minutes | failure_action_coverage_rate | gate_exception_count | overdue_exceptions_count | decision | reviewer | notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
""".lstrip()
    for row in rows:
        body += row + "\n"
    body += "\n## Update procedure\n1. step\n"
    return body


def _case_quality_with_stale_rule() -> str:
    return """
# Case Quality

- stale 判定条件: `today - last_reviewed_at > 30 days`
""".lstrip()


def _write_case_csv(path: Path, include_timestamp: bool) -> None:
    if include_timestamp:
        header = (
            "case_id,name,severity,question,expected_chunks,expected_keywords,golden_answer,"
            "category,owner,min_pass_rate,last_reviewed_at\n"
        )
        row = "T001,Case,S1,Question,,kw,,demo,owner,100,2026-03-29\n"
    else:
        header = (
            "case_id,name,severity,question,expected_chunks,expected_keywords,golden_answer,"
            "category,owner,min_pass_rate\n"
        )
        row = "T001,Case,S1,Question,,kw,,demo,owner,100\n"
    _write(path, header + row)


def test_collect_gate_summary_passes_when_c1_c4_satisfied(tmp_path: Path) -> None:
    register = tmp_path / "docs/ops/phase2-5-weekly-metrics-register.md"
    case_quality = tmp_path / "docs/ops/phase2-5-case-quality-weekly-review.md"

    _write(
        register,
        _register(
            [
                "| 2026-03-28 | 1 | https://example.com/1 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
                "| 2026-03-23 | 2 | https://example.com/2 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
                "| 2026-03-16 | 3 | https://example.com/3 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
                "| 2026-03-09 | 4 | https://example.com/4 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
            ]
        ),
    )
    _write(case_quality, _case_quality_with_stale_rule())

    pack_hr = tmp_path / "packs/hr/cases.csv"
    pack_demo = tmp_path / "packs/demo_cycle/cases.csv"
    _write_case_csv(pack_hr, include_timestamp=True)
    _write_case_csv(pack_demo, include_timestamp=True)

    summary = gate_check.collect_gate_summary(
        register_path=register,
        case_quality_weekly_review_path=case_quality,
        pack_case_paths=[pack_hr, pack_demo],
        required_weeks=4,
        coverage_threshold=1.0,
    )

    assert summary.c1_four_week_evidence_continuity is True
    assert summary.c2_overdue_exceptions_zero is True
    assert summary.c3_stale_timestamp_risk_resolved is True
    assert summary.c4_failure_action_coverage_threshold is True
    assert summary.overall_pass is True


def test_collect_gate_summary_fails_c1_when_weeks_are_insufficient(tmp_path: Path) -> None:
    register = tmp_path / "docs/ops/phase2-5-weekly-metrics-register.md"
    case_quality = tmp_path / "docs/ops/phase2-5-case-quality-weekly-review.md"

    _write(
        register,
        _register(
            [
                "| 2026-03-28 | 1 | https://example.com/1 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
                "| 2026-03-23 | 2 | https://example.com/2 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
                "| 2026-03-16 | 3 | https://example.com/3 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
            ]
        ),
    )
    _write(case_quality, _case_quality_with_stale_rule())

    pack_hr = tmp_path / "packs/hr/cases.csv"
    _write_case_csv(pack_hr, include_timestamp=True)

    summary = gate_check.collect_gate_summary(
        register_path=register,
        case_quality_weekly_review_path=case_quality,
        pack_case_paths=[pack_hr],
        required_weeks=4,
        coverage_threshold=1.0,
    )

    assert summary.c1_four_week_evidence_continuity is False
    assert summary.overall_pass is False
    assert any("insufficient weeks" in note for note in summary.notes)


def test_collect_gate_summary_fails_c3_when_timestamp_column_missing(tmp_path: Path) -> None:
    register = tmp_path / "docs/ops/phase2-5-weekly-metrics-register.md"
    case_quality = tmp_path / "docs/ops/phase2-5-case-quality-weekly-review.md"

    _write(
        register,
        _register(
            [
                "| 2026-03-28 | 1 | https://example.com/1 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
                "| 2026-03-23 | 2 | https://example.com/2 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
                "| 2026-03-16 | 3 | https://example.com/3 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
                "| 2026-03-09 | 4 | https://example.com/4 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | me | ok |",
            ]
        ),
    )
    _write(case_quality, _case_quality_with_stale_rule())

    pack_hr = tmp_path / "packs/hr/cases.csv"
    _write_case_csv(pack_hr, include_timestamp=False)

    summary = gate_check.collect_gate_summary(
        register_path=register,
        case_quality_weekly_review_path=case_quality,
        pack_case_paths=[pack_hr],
        required_weeks=4,
        coverage_threshold=1.0,
    )

    assert summary.c1_four_week_evidence_continuity is True
    assert summary.c3_stale_timestamp_risk_resolved is False
    assert summary.overall_pass is False
    assert len(summary.packs_missing_timestamp_column) == 1
    assert (
        summary.packs_missing_timestamp_column[0].replace("\\", "/").endswith("/packs/hr/cases.csv")
    )
