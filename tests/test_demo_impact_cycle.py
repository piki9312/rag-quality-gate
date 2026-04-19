"""Smoke tests for impact_cycle demo module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from rqg.demo.impact_cycle import (
    BROKEN_DOC,
    GOOD_DOC,
    DemoSummary,
    run_demo,
)


@pytest.fixture(autouse=True)
def _isolate_demo(tmp_path, monkeypatch):
    """Redirect demo work dir to tmp_path for test isolation."""
    monkeypatch.setattr("rqg.demo.impact_cycle.WORK_ROOT", tmp_path)
    monkeypatch.setattr("rqg.demo.impact_cycle.PACK_DIR", tmp_path / "pack")
    monkeypatch.setattr(
        "rqg.demo.impact_cycle.DOC_PATH",
        tmp_path / "pack" / "documents" / "leave_policy.md",
    )
    monkeypatch.setattr("rqg.demo.impact_cycle.SUMMARY_PATH", tmp_path / "summary.json")
    monkeypatch.setattr("rqg.demo.impact_cycle.PHASE1_DIR", tmp_path / "01-pass")
    monkeypatch.setattr("rqg.demo.impact_cycle.PHASE2_DIR", tmp_path / "02-fail-and-impact")
    monkeypatch.setattr("rqg.demo.impact_cycle.PHASE3_DIR", tmp_path / "03-fix-pass")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")


def test_good_and_broken_doc_constants():
    """GOOD_DOC and BROKEN_DOC are non-empty and differ."""
    assert len(GOOD_DOC.strip()) > 20
    assert len(BROKEN_DOC.strip()) > 20
    assert GOOD_DOC != BROKEN_DOC


def test_demo_summary_fields():
    summary = DemoSummary(
        run_id="test-run",
        old_snapshot="/tmp/old.json",
        new_snapshot="/tmp/new.json",
        generated_cases="/tmp/cases.json",
        impact_report="/tmp/impact.json",
        impact_review="/tmp/review.md",
        changed_evidence_ids=["ev-1"],
        impacted_case_ids=["case-1"],
        phase1_gate="pass",
        phase2_gate="fail",
        phase3_gate="pass",
    )
    assert summary.run_id == "test-run"
    assert summary.phase2_gate == "fail"


def _make_cli_side_effect(tmp_path):
    """Build a cli_main side effect that simulates the demo pipeline."""
    phase_statuses = ["pass", "fail", "pass"]
    phase_counter = {"eval_check": 0}

    def side_effect(argv):
        cmd = argv[0]

        if cmd == "eval":
            log_dir = None
            for i, arg in enumerate(argv):
                if arg == "--log-dir" and i + 1 < len(argv):
                    log_dir = argv[i + 1]
            if log_dir:
                idx_dir = None
                for i, arg in enumerate(argv):
                    if arg == "--index-dir" and i + 1 < len(argv):
                        idx_dir = argv[i + 1]
                if idx_dir:
                    snap_dir = Path(idx_dir) / "snapshots"
                    snap_dir.mkdir(parents=True, exist_ok=True)
                    (snap_dir / "demo.json").write_text(
                        json.dumps({"snapshot_id": "demo"}), encoding="utf-8"
                    )
            return 0

        elif cmd == "check":
            idx = phase_counter["eval_check"]
            phase_counter["eval_check"] += 1
            log_dir = None
            for i, arg in enumerate(argv):
                if arg == "--log-dir" and i + 1 < len(argv):
                    log_dir = argv[i + 1]
            if log_dir:
                log_path = Path(log_dir)
                log_path.mkdir(parents=True, exist_ok=True)
                status = phase_statuses[idx]
                (log_path / "gate-decision.json").write_text(
                    json.dumps({"status": status}), encoding="utf-8"
                )
                (log_path / "gate-report.md").write_text("# Report", encoding="utf-8")
            return 0 if phase_statuses[idx] == "pass" else 1

        elif cmd == "init-snapshot":
            output = None
            content = "sample"
            snapshot_id = "demo"
            doc_id = "demo"
            title = "Demo"
            source_path = "demo.md"
            for i, arg in enumerate(argv):
                if arg == "--output" and i + 1 < len(argv):
                    output = argv[i + 1]
                elif arg == "--snapshot-id" and i + 1 < len(argv):
                    snapshot_id = argv[i + 1]
                elif arg == "--doc-id" and i + 1 < len(argv):
                    doc_id = argv[i + 1]
                elif arg == "--title" and i + 1 < len(argv):
                    title = argv[i + 1]
                elif arg == "--source-path" and i + 1 < len(argv):
                    source_path = argv[i + 1]
                elif arg == "--content" and i + 1 < len(argv):
                    content = argv[i + 1]
            if output:
                import hashlib

                p = Path(output)
                p.parent.mkdir(parents=True, exist_ok=True)
                snap = {
                    "snapshot_id": snapshot_id,
                    "doc_id": doc_id,
                    "title": title,
                    "source_path": source_path,
                    "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                    "created_at": "2026-01-01T00:00:00Z",
                    "metadata": {},
                }
                p.write_text(json.dumps(snap, indent=2), encoding="utf-8")
            return 0

        elif cmd == "gen-cases":
            output = None
            for i, arg in enumerate(argv):
                if arg == "--output" and i + 1 < len(argv):
                    output = argv[i + 1]
                elif arg == "--review-output" and i + 1 < len(argv):
                    rp = Path(argv[i + 1])
                    rp.parent.mkdir(parents=True, exist_ok=True)
                    rp.write_text("# Review", encoding="utf-8")
            if output:
                p = Path(output)
                p.parent.mkdir(parents=True, exist_ok=True)
                cases = [
                    {
                        "case_id": "test-001",
                        "question": "What is leave policy?",
                        "expected_evidence": ["leave_policy.md#sec-1"],
                        "expected_keywords": ["leave"],
                        "risk_level": "S2",
                        "doc_snapshot_id": "impact-old",
                    }
                ]
                p.write_text(json.dumps(cases, indent=2), encoding="utf-8")
            return 0

        elif cmd == "impact":
            output = None
            review_output = None
            for i, arg in enumerate(argv):
                if arg == "--output" and i + 1 < len(argv):
                    output = argv[i + 1]
                elif arg == "--review-output" and i + 1 < len(argv):
                    review_output = argv[i + 1]
            if output:
                p = Path(output)
                p.parent.mkdir(parents=True, exist_ok=True)
                report = {
                    "changed_evidence_ids": ["leave_policy.md#sec-1"],
                    "impacted_case_ids": ["test-001"],
                }
                p.write_text(json.dumps(report, indent=2), encoding="utf-8")
            if review_output:
                rp = Path(review_output)
                rp.parent.mkdir(parents=True, exist_ok=True)
                rp.write_text("# Impact Review", encoding="utf-8")
            return 0

        return 0

    return side_effect


def test_run_demo_smoke(tmp_path):
    """Run the full impact_cycle demo with mocked cli_main calls."""
    side_effect = _make_cli_side_effect(tmp_path)

    with patch("rqg.demo.impact_cycle.cli_main", side_effect=side_effect):
        summary = run_demo()

    assert summary.phase1_gate == "pass"
    assert summary.phase2_gate == "fail"
    assert summary.phase3_gate == "pass"
    assert len(summary.changed_evidence_ids) > 0
    assert len(summary.impacted_case_ids) > 0

    summary_path = tmp_path / "summary.json"
    assert summary_path.exists(), "Summary JSON should be written"
