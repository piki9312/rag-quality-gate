from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from rqg.demo import phase2_5_keyword_miss_kpi as kpi


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    path.write_text(payload, encoding="utf-8")


def test_main_exports_review_template_and_summary(tmp_path: Path) -> None:
    results = tmp_path / "results.jsonl"
    output = tmp_path / "summary.json"
    review_template = tmp_path / "review.csv"
    cases = tmp_path / "cases.csv"

    _write_jsonl(
        results,
        [
            {
                "run_id": "run-001",
                "case_id": "HR001",
                "severity": "S1",
                "category": "deadline",
                "failure_type": "keyword_miss",
                "failure_reason": "Keyword match 75% < 80%",
                "answer": "有給休暇は5営業日前までに申請してください。",
            },
            {
                "run_id": "run-001",
                "case_id": "HR002",
                "failure_type": "retrieval_miss",
                "answer": "n/a",
            },
        ],
    )

    cases.write_text(
        "case_id,expected_keywords\n"
        "HR001,有給;申請;営業日;5営業日前\n"
        "HR002,有給;申請;システム\n",
        encoding="utf-8",
    )

    exit_code = kpi.main(
        [
            "--results-jsonl",
            str(results),
            "--cases-csv",
            str(cases),
            "--export-review-csv",
            str(review_template),
            "--output",
            str(output),
            "--week-start",
            "2026-03-23",
        ]
    )

    assert exit_code == 1
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["week_start"] == "2026-03-23"
    assert summary["run_id"] == "run-001"
    assert summary["keyword_miss_total"] == 1
    assert summary["reviewed_total"] == 0
    assert summary["false_negative_rate"] is None
    assert summary["decision"] == "investigate"

    with review_template.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 1
    assert rows[0]["case_id"] == "HR001"
    assert rows[0]["expected_keywords"] == "有給;申請;営業日;5営業日前"
    assert rows[0]["review_verdict"] == ""


def test_collect_summary_keep_going_when_reviewed_false_negative_rate_is_low(
    tmp_path: Path,
) -> None:
    results = tmp_path / "results.jsonl"
    review = tmp_path / "review.csv"

    _write_jsonl(
        results,
        [
            {
                "run_id": "run-002",
                "case_id": "HR001",
                "failure_type": "keyword_miss",
            }
        ],
    )
    review.write_text(
        "case_id,review_verdict\n" "HR001,valid_failure\n",
        encoding="utf-8",
    )

    summary = kpi.collect_summary(
        results,
        review_csv=review,
        today=date(2026, 3, 30),
        week_start_override=date(2026, 3, 23),
        max_false_negative_rate=0.2,
    )

    assert summary.week_start == "2026-03-23"
    assert summary.run_id == "run-002"
    assert summary.reviewed_total == 1
    assert summary.false_negative_count == 0
    assert summary.false_negative_rate == 0.0
    assert summary.decision == "keep-going"


def test_collect_summary_investigate_when_false_negative_rate_exceeds_threshold(
    tmp_path: Path,
) -> None:
    results = tmp_path / "results.jsonl"
    review = tmp_path / "review.csv"

    _write_jsonl(
        results,
        [
            {
                "run_id": "run-003",
                "case_id": "HR001",
                "failure_type": "keyword_miss",
            }
        ],
    )
    review.write_text(
        "case_id,review_verdict\n" "HR001,false_negative\n",
        encoding="utf-8",
    )

    summary = kpi.collect_summary(
        results,
        review_csv=review,
        today=date(2026, 3, 30),
        max_false_negative_rate=0.2,
    )

    assert summary.reviewed_total == 1
    assert summary.false_negative_count == 1
    assert summary.false_negative_rate == 1.0
    assert summary.decision == "investigate"
