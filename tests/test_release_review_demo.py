from __future__ import annotations

import csv
import json
from pathlib import Path

from rqg.cli import main
from rqg.quality.change_event import load_change_event_file

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = REPO_ROOT / "packs" / "release_review_demo"


def test_release_review_demo_assets_are_complete_and_safe() -> None:
    change_event_path = PACK_DIR / "change-event.yml"
    change_event = load_change_event_file(change_event_path)

    assert change_event is not None
    assert change_event.change_type == "document_update"
    assert change_event.affected_business_categories == ["pricing", "refund", "cancellation"]
    assert change_event.target_release == ""

    change_text = change_event_path.read_text(encoding="utf-8")
    for forbidden in ("target_release:", "path:", "C:/", "C:\\\\", "customer", "secret"):
        assert forbidden not in change_text

    rows = list(csv.DictReader((PACK_DIR / "cases.csv").open(encoding="utf-8", newline="")))

    assert 10 <= len(rows) <= 20
    assert {row["risk_domain"] for row in rows} >= {
        "pricing",
        "refund",
        "cancellation",
        "contract_terms",
        "campaign",
    }
    assert all(row["expected_answer"].strip() for row in rows)
    assert all(row["expected_evidence"].strip() for row in rows)
    assert all(row["required_action"].strip() for row in rows)

    s1_rows = [row for row in rows if row["status"] == "active" and row["severity"] == "S1"]
    assert len(s1_rows) >= 5
    for row in s1_rows:
        assert "manual_review_required" in row["notes"]
        assert "pattern:FP-" in row["notes"]

    readme = (PACK_DIR / "README.md").read_text(encoding="utf-8")
    for required_text in (
        "change-event.yml を書く",
        "rqg gate --change-event change-event.yml",
        "Change Event Card",
        "Decision Card",
        "Major Failures",
        "Document Corpus Card",
        "Production Readiness Card",
        "Report Preview",
    ):
        assert required_text in readme


def test_release_review_demo_gate_produces_no_go_review_packet(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    index_dir = tmp_path / "index"
    log_dir = tmp_path / "runs"

    exit_code = main(
        [
            "gate",
            "--pack",
            str(PACK_DIR),
            "--mock",
            "--change-event",
            str(PACK_DIR / "change-event.yml"),
            "--index-dir",
            str(index_dir),
            "--log-dir",
            str(log_dir),
            "--reset-log-dir",
        ]
    )

    assert exit_code == 1

    bundle = json.loads((log_dir / "gate-report.json").read_text(encoding="utf-8"))
    review_packet = bundle["review_packet"]

    assert bundle["decision"]["policy_status"] == "block"
    assert review_packet["decision"]["customer_status"] == "No-Go"
    assert review_packet["change_summary"]["change_type"] == "document_update"
    assert review_packet["production_readiness"]["status"] == "not_ready"
    assert review_packet["document_corpus"]["document_count"] >= 3
    assert review_packet["report_sections"]["change_summary"]
    assert review_packet["report_sections"]["production_readiness"]

    titles = {item["title"] for item in review_packet["document_corpus"]["target_documents"]}
    assert {"pricing_policy.md", "refund_policy.md", "cancellation_policy.md"} <= titles

    failures = review_packet["major_failures"]
    assert failures
    assert any(item["customer_severity"] in {"Critical", "High"} for item in failures)
    assert any(
        item["business_category"] in {"refund", "cancellation", "pricing", "contract_terms"}
        for item in failures
    )
