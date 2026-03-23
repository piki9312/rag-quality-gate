"""Reproducible ingest -> impact -> fail/fix/pass demo for Phase 1.5."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from rqg.cli import main as cli_main


@dataclass
class DemoSummary:
    run_id: str
    old_snapshot: str
    new_snapshot: str
    generated_cases: str
    impact_report: str
    impact_review: str
    changed_evidence_ids: list[str]
    impacted_case_ids: list[str]
    phase1_gate: str
    phase2_gate: str
    phase3_gate: str


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PACK_DIR = REPO_ROOT / "packs" / "demo_cycle"
WORK_ROOT = REPO_ROOT / "demo_runs" / "impact_cycle" / uuid.uuid4().hex[:8]
PACK_DIR = WORK_ROOT / "pack"
DOC_PATH = PACK_DIR / "documents" / "leave_policy.md"
SUMMARY_PATH = WORK_ROOT / "summary.json"

PHASE1_DIR = WORK_ROOT / "01-pass"
PHASE2_DIR = WORK_ROOT / "02-fail-and-impact"
PHASE3_DIR = WORK_ROOT / "03-fix-pass"

GOOD_DOC = """# Leave Policy

Paid leave requests must be submitted 5 business days in advance.
Employees should submit the request through the HR system.
"""

BROKEN_DOC = """# Leave Policy

Paid leave requests should be discussed with the manager first.
Employees should ask HR if timing is unclear.
"""


def _prepare_pack() -> None:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE_PACK_DIR, PACK_DIR)


def _run_eval_and_check(phase_dir: Path) -> tuple[int, int, str, Path]:
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
    return eval_exit_code, check_exit_code, decision["status"], index_dir


def _latest_snapshot(index_dir: Path) -> Path:
    snapshot_dir = index_dir / "snapshots"
    candidates = sorted(snapshot_dir.glob("*.json"), key=lambda path: path.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No snapshots found under {snapshot_dir}")
    return candidates[-1]


def _init_snapshot_from_doc(doc_path: Path, output_path: Path, snapshot_id: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = doc_path.read_text(encoding="utf-8")
    exit_code = cli_main(
        [
            "init-snapshot",
            "--snapshot-id",
            snapshot_id,
            "--doc-id",
            "demo-leave-policy",
            "--title",
            "Leave Policy",
            "--source-path",
            str(doc_path),
            "--content",
            text,
            "--output",
            str(output_path),
        ]
    )
    if exit_code != 0:
        raise RuntimeError(f"Failed to create snapshot for {doc_path}")
    return output_path


def run_demo() -> DemoSummary:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    _prepare_pack()

    # Phase 1: ingest, case auto-generation, pass
    DOC_PATH.write_text(GOOD_DOC, encoding="utf-8")
    phase1_eval, phase1_check, phase1_gate, phase1_index = _run_eval_and_check(PHASE1_DIR)
    _latest_snapshot(phase1_index)

    (PHASE1_DIR / "artifacts").mkdir(parents=True, exist_ok=True)
    old_doc_copy = PHASE1_DIR / "artifacts" / "leave_policy_old.md"
    old_doc_copy.write_text(GOOD_DOC, encoding="utf-8")
    old_snapshot = _init_snapshot_from_doc(
        old_doc_copy,
        PHASE1_DIR / "artifacts" / "old_snapshot.json",
        "impact-old",
    )

    generated_cases = PHASE1_DIR / "artifacts" / "eval_cases.json"
    generated_review = PHASE1_DIR / "artifacts" / "eval_cases.md"
    gen_exit = cli_main(
        [
            "gen-cases",
            "--snapshot",
            str(old_snapshot),
            "--output",
            str(generated_cases),
            "--review-output",
            str(generated_review),
            "--mode",
            "rule",
        ]
    )

    if phase1_eval != 0 or phase1_check != 0 or phase1_gate != "pass" or gen_exit != 0:
        raise RuntimeError("Phase 1 failed during demo setup")

    # Phase 2: document update, impact extraction, fail gate
    DOC_PATH.write_text(BROKEN_DOC, encoding="utf-8")
    phase2_eval, phase2_check, phase2_gate, phase2_index = _run_eval_and_check(PHASE2_DIR)
    _latest_snapshot(phase2_index)

    (PHASE2_DIR / "artifacts").mkdir(parents=True, exist_ok=True)
    new_doc_copy = PHASE2_DIR / "artifacts" / "leave_policy_new.md"
    new_doc_copy.write_text(BROKEN_DOC, encoding="utf-8")
    new_snapshot = _init_snapshot_from_doc(
        new_doc_copy,
        PHASE2_DIR / "artifacts" / "new_snapshot.json",
        "impact-new",
    )

    impact_report_path = PHASE2_DIR / "artifacts" / "impact_report.json"
    impact_review_path = PHASE2_DIR / "artifacts" / "impact_review.md"
    impact_exit = cli_main(
        [
            "impact",
            "--old-snapshot",
            str(old_snapshot),
            "--new-snapshot",
            str(new_snapshot),
            "--cases",
            str(generated_cases),
            "--output",
            str(impact_report_path),
            "--review-output",
            str(impact_review_path),
        ]
    )
    if impact_exit != 0:
        raise RuntimeError("Impact analysis failed")

    impact_report = json.loads(impact_report_path.read_text(encoding="utf-8"))

    # Phase 3: fix and pass again
    DOC_PATH.write_text(GOOD_DOC, encoding="utf-8")
    phase3_eval, phase3_check, phase3_gate, _ = _run_eval_and_check(PHASE3_DIR)

    if phase2_gate != "fail":
        raise RuntimeError("Phase 2 expected a failing gate status")
    if phase3_eval != 0 or phase3_check != 0 or phase3_gate != "pass":
        raise RuntimeError("Phase 3 expected a recovered passing status")

    summary = DemoSummary(
        run_id=WORK_ROOT.name,
        old_snapshot=str(old_snapshot),
        new_snapshot=str(new_snapshot),
        generated_cases=str(generated_cases),
        impact_report=str(impact_report_path),
        impact_review=str(impact_review_path),
        changed_evidence_ids=impact_report.get("changed_evidence_ids", []),
        impacted_case_ids=impact_report.get("impacted_case_ids", []),
        phase1_gate=phase1_gate,
        phase2_gate=phase2_gate,
        phase3_gate=phase3_gate,
    )
    SUMMARY_PATH.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    return summary


def main() -> int:
    summary = run_demo()
    print(f"run_id={summary.run_id}")
    print(f"phase1_gate={summary.phase1_gate}")
    print(f"phase2_gate={summary.phase2_gate}")
    print(f"phase3_gate={summary.phase3_gate}")
    print(f"changed_evidence_count={len(summary.changed_evidence_ids)}")
    print(f"impacted_case_count={len(summary.impacted_case_ids)}")
    print(f"impact_report={summary.impact_report}")
    print(f"summary={SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
