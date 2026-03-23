"""Reproducible pass -> fail -> pass demo for the quality gate."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from rqg.cli import main as cli_main


@dataclass
class PhaseResult:
    name: str
    eval_exit_code: int
    check_exit_code: int
    gate_status: str
    decision_file: str
    report_file: str
    snapshot_dir: str


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PACK_DIR = REPO_ROOT / "packs" / "demo_cycle"
WORK_ROOT = REPO_ROOT / "demo_runs" / "fail_fix_cycle" / uuid.uuid4().hex[:8]
PACK_DIR = WORK_ROOT / "pack"
DOC_PATH = PACK_DIR / "documents" / "leave_policy.md"
SUMMARY_PATH = WORK_ROOT / "summary.json"

GOOD_DOC = """# Leave Policy

Paid leave requests must be submitted 5 business days in advance.
Employees should submit the request through the HR system.
"""

BROKEN_DOC = """# Leave Policy

Paid leave requests must be submitted through the HR system.
Employees should ask their manager if timing is unclear.
"""


def _prepare_pack() -> None:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE_PACK_DIR, PACK_DIR)


def _run_phase(name: str) -> PhaseResult:
    phase_dir = WORK_ROOT / name
    index_dir = phase_dir / "index"
    log_dir = phase_dir / "runs"
    report_file = log_dir / "gate-report.md"
    decision_file = log_dir / "gate-decision.json"

    eval_exit_code = cli_main(
        [
            "eval",
            str(PACK_DIR / "cases.csv"),
            "--docs",
            str(PACK_DIR / "documents"),
            "--mock",
            "--index-dir",
            str(index_dir),
            "--log-dir",
            str(log_dir),
        ]
    )
    check_exit_code = cli_main(
        [
            "check",
            "--log-dir",
            str(log_dir),
            "--config",
            str(PACK_DIR / "gate.yml"),
            "--output-file",
            str(report_file),
            "--decision-file",
            str(decision_file),
        ]
    )
    decision = json.loads(decision_file.read_text(encoding="utf-8"))

    return PhaseResult(
        name=name,
        eval_exit_code=eval_exit_code,
        check_exit_code=check_exit_code,
        gate_status=decision["status"],
        decision_file=str(decision_file),
        report_file=str(report_file),
        snapshot_dir=str(index_dir / "snapshots"),
    )


def run_demo() -> list[PhaseResult]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    _prepare_pack()

    DOC_PATH.write_text(GOOD_DOC, encoding="utf-8")
    first_pass = _run_phase("01-pass")

    DOC_PATH.write_text(BROKEN_DOC, encoding="utf-8")
    fail = _run_phase("02-fail")

    DOC_PATH.write_text(GOOD_DOC, encoding="utf-8")
    second_pass = _run_phase("03-pass")

    phases = [first_pass, fail, second_pass]
    SUMMARY_PATH.write_text(
        json.dumps([phase.__dict__ for phase in phases], indent=2),
        encoding="utf-8",
    )
    return phases


def main() -> int:
    phases = run_demo()
    for phase in phases:
        print(
            f"{phase.name}: eval={phase.eval_exit_code} "
            f"check={phase.check_exit_code} gate={phase.gate_status}"
        )
    print(f"Summary written to {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
