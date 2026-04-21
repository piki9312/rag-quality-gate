from __future__ import annotations

from datetime import datetime, timedelta, timezone

from rqg.quality.check import GateConfig, render_gate_markdown, run_check
from rqg.quality.models import QARunRecord, QATestCase
from rqg.quality.staleness import summarize_case_staleness


def test_summarize_case_staleness_uses_last_reviewed_and_updated_at() -> None:
    now = datetime(2026, 4, 21, tzinfo=timezone.utc)
    cases = [
        QATestCase(
            case_id="QA-fresh",
            name="fresh",
            question="q",
            severity="S2",
            owner="ops",
            updated_at="2026-04-20",
        ),
        QATestCase(
            case_id="QA-stale",
            name="stale",
            question="q",
            severity="S1",
            owner="owner-a",
            last_reviewed_at="2026-03-01",
        ),
        QATestCase(
            case_id="QA-missing",
            name="missing",
            question="q",
            severity="S2",
            owner="owner-b",
        ),
    ]

    summary = summarize_case_staleness(cases, stale_after_days=30, now=now)

    assert summary.total_cases == 3
    assert summary.fresh_cases == 1
    assert round(summary.fresh_rate, 1) == 33.3
    assert [item.case_id for item in summary.stale_cases] == ["QA-stale", "QA-missing"]
    assert summary.stale_cases[0].issue == "older than 30 days"
    assert summary.stale_cases[1].issue == "missing last_reviewed_at / updated_at"


def test_run_check_surfaces_stale_cases_in_gate_output(tmp_path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc)
    log_path = log_dir / today.strftime("%Y%m%d.jsonl")
    records = [
        QARunRecord(
            timestamp=today,
            run_id="run-stale-1",
            case_id="QA-1",
            severity="S2",
            passed=True,
        ),
        QARunRecord(
            timestamp=today,
            run_id="run-stale-1",
            case_id="QA-2",
            severity="S2",
            passed=True,
        ),
    ]
    log_path.write_text("\n".join(record.model_dump_json() for record in records) + "\n", encoding="utf-8")

    cases_path = tmp_path / "cases.csv"
    fresh_date = (today - timedelta(days=5)).date().isoformat()
    stale_date = (today - timedelta(days=45)).date().isoformat()
    cases_path.write_text(
        "\n".join(
            [
                "case_id,name,status,severity,eval_mode,question,expected_answer,expected_evidence,expected_keywords,category,source_doc,owner,min_case_score,updated_at,last_reviewed_at,notes",
                f"QA-1,Fresh case,active,S2,evidence_keyword,Fresh?,,,fresh,policy,policy.md,ops,0,{fresh_date},{fresh_date},",
                f"QA-2,Stale case,active,S2,evidence_keyword,Stale?,,,stale,policy,policy.md,ops,0,{stale_date},{stale_date},",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_check(
        str(log_dir),
        GateConfig(
            s1_pass_rate=0.0,
            overall_pass_rate=0.0,
            case_staleness_days=30,
            min_fresh_case_review_rate=100.0,
        ),
        days=1,
        cases_file=str(cases_path),
    )

    markdown = render_gate_markdown(result)

    assert result.gate_status == "fail"
    assert result.fresh_case_review_rate == 50.0
    assert result.fresh_case_count == 1
    assert result.fresh_case_total == 2
    assert len(result.stale_cases) == 1
    assert result.stale_cases[0].case_id == "QA-2"
    assert "### Case Staleness" in markdown
    assert "Fresh review rate: 50.0% (1/2) within 30 days" in markdown
    assert "| QA-2 | S2 | ops |" in markdown