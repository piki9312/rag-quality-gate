from __future__ import annotations

import csv
from pathlib import Path

from rqg.cli import main

DEMO_ROOT = Path("demo_internal")
CASES_PATH = DEMO_ROOT / "casegen" / "cases.csv"
REVIEW_PATH = DEMO_ROOT / "casegen" / "s1_case_review.csv"
PATTERNS_PATH = DEMO_ROOT / "casegen" / "failure_patterns.md"
DOC_PATH = DEMO_ROOT / "documents" / "customer_support_policy.md"
RUNBOOK_PATH = Path("docs/demo/internal-s1-case-authoring.md")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_internal_s1_demo_cases_are_three_active_s1_rows() -> None:
    rows = _read_csv(CASES_PATH)

    assert len(rows) == 3
    for row in rows:
        assert row["status"] == "active"
        assert row["severity"] == "S1"
        assert row["owner"] == "proofgate-demo-owner"
        assert row["last_reviewed_at"] == "2026-05-11"
        assert "manual_review_required" in row["notes"]
        assert "pattern:FP-" in row["notes"]
        assert "block_reason:" in row["notes"]


def test_internal_s1_demo_review_csv_tracks_same_cases() -> None:
    review_rows = _read_csv(REVIEW_PATH)

    assert len(review_rows) == 3
    assert {row["case_id"] for row in review_rows} == {
        "DEMO-S1-REFUND-001",
        "DEMO-S1-CANCEL-001",
        "DEMO-S1-PRIVACY-001",
    }
    assert all(row["approval_status"] == "approved" for row in review_rows)


def test_internal_s1_demo_failure_patterns_are_limited_to_three_s1_examples() -> None:
    text = PATTERNS_PATH.read_text(encoding="utf-8")

    assert "FP-REFUND-001" in text
    assert "FP-CANCEL-001" in text
    assert "FP-PRIVACY-001" in text
    assert "parser" in text
    assert "正本ではありません" in text


def test_internal_s1_demo_policy_and_runbook_mark_simulation_only() -> None:
    assert "完全なサンプルデータ" in DOC_PATH.read_text(encoding="utf-8")

    runbook = RUNBOOK_PATH.read_text(encoding="utf-8")
    assert "SIMULATION ONLY" in runbook
    assert "顧客品質証跡ではありません" in runbook
    assert "S1 active case の自動生成" in runbook


def test_internal_s1_demo_pack_passes_strict_validate_pack() -> None:
    exit_code = main(
        [
            "validate-pack",
            "--pack-dir",
            str(DEMO_ROOT),
            "--strict-s1-governance",
        ]
    )

    assert exit_code == 0
