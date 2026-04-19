"""Smoke tests for fail_fix_cycle demo module."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from rqg.demo.fail_fix_cycle import (
    BROKEN_DOC,
    GOOD_DOC,
    PhaseResult,
    run_demo,
)


@pytest.fixture(autouse=True)
def _isolate_demo(tmp_path, monkeypatch):
    """Redirect demo work dir to tmp_path for test isolation."""
    monkeypatch.setattr("rqg.demo.fail_fix_cycle.WORK_ROOT", tmp_path)
    monkeypatch.setattr("rqg.demo.fail_fix_cycle.PACK_DIR", tmp_path / "pack")
    monkeypatch.setattr(
        "rqg.demo.fail_fix_cycle.DOC_PATH",
        tmp_path / "pack" / "documents" / "leave_policy.md",
    )
    monkeypatch.setattr("rqg.demo.fail_fix_cycle.SUMMARY_PATH", tmp_path / "summary.json")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")


def test_good_and_broken_doc_constants():
    """GOOD_DOC and BROKEN_DOC are non-empty and differ."""
    assert len(GOOD_DOC.strip()) > 20
    assert len(BROKEN_DOC.strip()) > 20
    assert GOOD_DOC != BROKEN_DOC


def test_phase_result_fields():
    pr = PhaseResult(
        name="test",
        eval_exit_code=0,
        check_exit_code=0,
        gate_status="pass",
        decision_file="/tmp/d.json",
        report_file="/tmp/r.md",
        snapshot_dir="/tmp/snap",
    )
    assert pr.name == "test"
    assert pr.gate_status == "pass"


def _make_cli_side_effect(tmp_path, phase_statuses):
    """Build a cli_main side effect that writes gate-decision.json for each phase."""
    phase_counter = {"eval": 0, "check": 0}

    def side_effect(argv):
        cmd = argv[0]
        if cmd == "eval":
            idx = phase_counter["eval"]
            phase_counter["eval"] += 1
            log_dir = None
            for i, arg in enumerate(argv):
                if arg == "--log-dir" and i + 1 < len(argv):
                    log_dir = argv[i + 1]
            return 0
        elif cmd == "check":
            idx = phase_counter["check"]
            phase_counter["check"] += 1
            log_dir = None
            for i, arg in enumerate(argv):
                if arg == "--log-dir" and i + 1 < len(argv):
                    log_dir = argv[i + 1]
            if log_dir:
                from pathlib import Path

                log_path = Path(log_dir)
                log_path.mkdir(parents=True, exist_ok=True)
                decision = {"status": phase_statuses[idx]}
                (log_path / "gate-decision.json").write_text(json.dumps(decision), encoding="utf-8")
                (log_path / "gate-report.md").write_text("# Report", encoding="utf-8")
            return 0 if phase_statuses[idx] == "pass" else 1
        return 0

    return side_effect


def test_run_demo_smoke(tmp_path):
    """Run the full fail_fix_cycle demo with mocked cli_main calls."""
    phase_statuses = ["pass", "fail", "pass"]
    side_effect = _make_cli_side_effect(tmp_path, phase_statuses)

    with patch("rqg.demo.fail_fix_cycle.cli_main", side_effect=side_effect):
        phases = run_demo()

    assert len(phases) == 3
    assert phases[0].gate_status == "pass", "Phase 1 should pass"
    assert phases[1].gate_status == "fail", "Phase 2 should fail"
    assert phases[2].gate_status == "pass", "Phase 3 should pass again"

    summary_path = tmp_path / "summary.json"
    assert summary_path.exists(), "Summary JSON should be written"
