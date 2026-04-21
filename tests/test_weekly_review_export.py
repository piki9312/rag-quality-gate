from __future__ import annotations

import json
import uuid
from pathlib import Path

from rqg.cli import main
from rqg.quality.weekly_review import build_weekly_review_issue_payload


def test_build_weekly_review_issue_payload_from_summary() -> None:
    payload = build_weekly_review_issue_payload(
        {
            "entries": 3,
            "week_start": "2026-04-20",
            "status_mix": {"pass": 0, "warn": 1, "fail": 2},
            "summary_lines": [
                "- Latest status: FAIL (run-3)",
                "- Failure action coverage (last 3): 2/3 categories (66.7%)",
                "",
                "### Latest Change Summary",
                "- Compared runs: run-2 -> run-3",
            ],
            "trend": {"latest_run_id": "run-3", "latest_status": "FAIL"},
            "failure_action_coverage": {
                "total_categories": 3,
                "covered_categories": 2,
                "coverage_rate": 66.7,
                "window_size": 3,
            },
            "review_steward": "ops-team",
            "stale_case_review": {
                "stale_after_days": 30,
                "fresh_case_review_rate": 75.0,
                "fresh_case_count": 3,
                "total_cases": 4,
                "stale_cases_count": 1,
                "owners": [
                    {
                        "owner": "hr-team",
                        "stale_count": 1,
                        "case_ids": ["QA-9"],
                        "highest_age_days": 34,
                    }
                ],
                "stale_cases": [
                    {
                        "case_id": "QA-9",
                        "owner": "hr-team",
                        "severity": "S1",
                        "age_days": 34,
                        "reference_field": "last_reviewed_at",
                        "reference_value": "2026-03-17",
                        "issue": "older than 30 days",
                    }
                ],
            },
            "uncovered_categories": [
                {
                    "failure_category": "unknown",
                    "total_count": 2,
                    "last_seen_run_id": "run-3",
                    "affected_case_ids": ["QA-7", "QA-8"],
                }
            ],
        },
        labels=["phase2-5", "weekly-review", "ops"],
    )

    assert payload["issue_needed"] is True
    assert payload["labels"] == ["phase2-5", "weekly-review", "ops"]
    assert payload["title"] == "[Phase2.5][Weekly Review] 2026-04-20"
    assert "Week start: 2026-04-20" in payload["body"]
    assert "Weekly review steward: ops-team" in payload["body"]
    assert "## Triage Summary" in payload["body"]
    assert "Action required: 1 uncovered category, 1 stale active case" in payload["body"]
    assert "| unknown | 2 | run-3 | QA-7, QA-8 |" in payload["body"]
    assert "### Stale Cases By Owner" in payload["body"]
    assert "| hr-team | 1 | 34 | QA-9 |" in payload["body"]
    assert "## Recent History" in payload["body"]
    assert "#### Latest Change Summary" in payload["body"]
    assert "## Required Actions" in payload["body"]
    assert payload["review_steward"] == "ops-team"
    assert payload["summary"]["stale_cases_count"] == 1


def test_export_weekly_review_command_writes_issue_payload(capsys) -> None:
    tmp_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-weekly-review"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    summary_path = tmp_dir / "gate-history-summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "entries": 2,
                "week_start": "2026-04-20",
                "status_mix": {"pass": 0, "warn": 0, "fail": 2},
                "summary_lines": ["- Latest status: FAIL (run-2)"],
                "trend": {"latest_run_id": "run-2", "latest_status": "FAIL"},
                "failure_action_coverage": {
                    "total_categories": 2,
                    "covered_categories": 1,
                    "coverage_rate": 50.0,
                    "window_size": 2,
                },
                "review_steward": "ops-team",
                "stale_case_review": {
                    "stale_after_days": 30,
                    "fresh_case_review_rate": 50.0,
                    "fresh_case_count": 1,
                    "total_cases": 2,
                    "stale_cases_count": 1,
                    "owners": [
                        {
                            "owner": "hr-team",
                            "stale_count": 1,
                            "case_ids": ["QA-9"],
                            "highest_age_days": 31,
                        }
                    ],
                    "stale_cases": [
                        {
                            "case_id": "QA-9",
                            "owner": "hr-team",
                            "severity": "S2",
                            "age_days": 31,
                            "reference_field": "last_reviewed_at",
                            "reference_value": "2026-03-20",
                            "issue": "older than 30 days",
                        }
                    ],
                },
                "uncovered_categories": [
                    {
                        "failure_category": "unknown",
                        "total_count": 1,
                        "last_seen_run_id": "run-2",
                        "affected_case_ids": ["QA-4"],
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    output_path = tmp_dir / "weekly-review-issue.json"
    exit_code = main(
        [
            "export-weekly-review",
            "--summary-file",
            str(summary_path),
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert output_path.exists()
    assert "Saved weekly review issue payload" in captured.out
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["issue_needed"] is True
    assert payload["summary"]["coverage_rate"] == 50.0
    assert payload["summary"]["week_start"] == "2026-04-20"
    assert payload["summary"]["stale_cases_count"] == 1
    assert payload["uncovered_categories"][0]["failure_category"] == "unknown"
    assert payload["review_steward"] == "ops-team"
    assert payload["title"] == "[Phase2.5][Weekly Review] 2026-04-20"
    assert "## Required Actions" in payload["body"]


def test_build_weekly_review_issue_payload_is_needed_for_stale_cases_even_without_uncovered_categories() -> None:
    payload = build_weekly_review_issue_payload(
        {
            "entries": 1,
            "week_start": "2026-04-20",
            "status_mix": {"pass": 1, "warn": 0, "fail": 0},
            "trend": {"latest_run_id": "run-1", "latest_status": "PASS"},
            "failure_action_coverage": {
                "total_categories": 0,
                "covered_categories": 0,
                "coverage_rate": 0.0,
                "window_size": 1,
            },
            "stale_case_review": {
                "stale_after_days": 30,
                "fresh_case_review_rate": 50.0,
                "fresh_case_count": 1,
                "total_cases": 2,
                "stale_cases_count": 1,
                "owners": [{"owner": "hr-team", "stale_count": 1, "case_ids": ["QA-1"], "highest_age_days": 40}],
                "stale_cases": [{"case_id": "QA-1", "owner": "hr-team", "severity": "S1", "age_days": 40, "reference_field": "last_reviewed_at", "reference_value": "2026-03-11", "issue": "older than 30 days"}],
            },
            "uncovered_categories": [],
        }
    )

    assert payload["issue_needed"] is True
    assert "Action required: 1 stale active case" in payload["body"]


def test_build_weekly_review_issue_payload_formats_no_action_state() -> None:
    payload = build_weekly_review_issue_payload(
        {
            "entries": 2,
            "week_start": "2026-04-20",
            "status_mix": {"pass": 1, "warn": 1, "fail": 0},
            "trend": {"latest_run_id": "run-2", "latest_status": "WARN"},
            "review_steward": "ops-team",
            "uncovered_categories": [],
        }
    )

    assert payload["issue_needed"] is False
    assert "Action required: no immediate owner action (0 uncovered categories, 0 stale active cases)" in payload["body"]
    assert "Review the recent history summary below and close or archive this issue" in payload["body"]


def test_export_weekly_review_command_returns_error_when_summary_missing(capsys) -> None:
    missing_path = Path("tests/.tmp") / f"{uuid.uuid4()}-missing" / "gate-history-summary.json"

    exit_code = main(["export-weekly-review", "--summary-file", str(missing_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No gate history summary found" in captured.out