"""Quickstart onboarding demo for first-time users.

Flow:
1. ingest
2. gen-cases
3. eval
4. check
5. impact
6. review output
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from rqg.cli import main as cli_main


@dataclass
class QuickstartSummary:
    run_id: str
    old_snapshot: str
    new_snapshot: str
    generated_cases: str
    generated_cases_review: str
    impact_report: str
    impact_review: str
    gate_status: str
    changed_evidence_count: int
    impacted_case_count: int


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PACK_DIR = REPO_ROOT / "packs" / "demo_cycle"
WORK_ROOT = REPO_ROOT / "demo_runs" / "onboarding_quickstart" / uuid.uuid4().hex[:8]
PACK_DIR = WORK_ROOT / "pack"
DOC_PATH = PACK_DIR / "documents" / "leave_policy.md"
SUMMARY_PATH = WORK_ROOT / "summary.json"

GOOD_DOC = """# Leave Policy

Paid leave requests must be submitted 5 business days in advance.
Employees should submit the request through the HR system.
"""

UPDATED_DOC = """# Leave Policy

Paid leave requests must be submitted 3 business days in advance.
Employees should submit the request through the HR system.
"""


def _run_cli(args: list[str], step: str) -> None:
    exit_code = cli_main(args)
    if exit_code != 0:
        raise RuntimeError(f"{step} failed with exit code {exit_code}")


def _prepare_pack() -> None:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE_PACK_DIR, PACK_DIR)


def _init_snapshot_from_doc(doc_path: Path, output_path: Path, snapshot_id: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = doc_path.read_text(encoding="utf-8")
    _run_cli(
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
        ],
        step="init-snapshot",
    )
    return output_path


def run_demo() -> QuickstartSummary:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    _prepare_pack()

    artifacts_dir = WORK_ROOT / "artifacts"
    index_dir = WORK_ROOT / "index"
    log_dir = WORK_ROOT / "runs"
    report_file = log_dir / "gate-report.md"
    decision_file = log_dir / "gate-decision.json"

    DOC_PATH.write_text(GOOD_DOC, encoding="utf-8")

    # 1) ingest
    _run_cli(
        [
            "ingest",
            str(PACK_DIR / "documents"),
            "--index-dir",
            str(index_dir),
        ],
        step="ingest",
    )

    # Build a stable old snapshot from a copied file to avoid path-overwrite issues.
    old_doc_copy = artifacts_dir / "leave_policy_old.md"
    old_doc_copy.parent.mkdir(parents=True, exist_ok=True)
    old_doc_copy.write_text(GOOD_DOC, encoding="utf-8")
    old_snapshot = _init_snapshot_from_doc(
        old_doc_copy,
        artifacts_dir / "old_snapshot.json",
        "quickstart-old",
    )

    # 2) gen-cases
    generated_cases = artifacts_dir / "eval_cases.json"
    generated_cases_review = artifacts_dir / "eval_cases_review.md"
    _run_cli(
        [
            "gen-cases",
            "--snapshot",
            str(old_snapshot),
            "--output",
            str(generated_cases),
            "--review-output",
            str(generated_cases_review),
            "--mode",
            "rule",
        ],
        step="gen-cases",
    )

    # 3) eval
    _run_cli(
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
        ],
        step="eval",
    )

    # 4) check
    _run_cli(
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
        ],
        step="check",
    )

    decision = json.loads(decision_file.read_text(encoding="utf-8"))

    # Prepare updated document and new snapshot for impact.
    DOC_PATH.write_text(UPDATED_DOC, encoding="utf-8")
    new_doc_copy = artifacts_dir / "leave_policy_new.md"
    new_doc_copy.write_text(UPDATED_DOC, encoding="utf-8")
    new_snapshot = _init_snapshot_from_doc(
        new_doc_copy,
        artifacts_dir / "new_snapshot.json",
        "quickstart-new",
    )

    # 5) impact
    impact_report_path = artifacts_dir / "impact_report.json"
    impact_review_path = artifacts_dir / "impact_review.md"
    _run_cli(
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
        ],
        step="impact",
    )

    impact_payload = json.loads(impact_report_path.read_text(encoding="utf-8"))

    summary = QuickstartSummary(
        run_id=WORK_ROOT.name,
        old_snapshot=str(old_snapshot),
        new_snapshot=str(new_snapshot),
        generated_cases=str(generated_cases),
        generated_cases_review=str(generated_cases_review),
        impact_report=str(impact_report_path),
        impact_review=str(impact_review_path),
        gate_status=decision.get("status", "unknown"),
        changed_evidence_count=len(impact_payload.get("changed_evidence_ids", [])),
        impacted_case_count=len(impact_payload.get("impacted_case_ids", [])),
    )
    SUMMARY_PATH.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    return summary


def main() -> int:
    summary = run_demo()
    print(f"run_id={summary.run_id}")
    print(f"gate_status={summary.gate_status}")
    print(f"changed_evidence_count={summary.changed_evidence_count}")
    print(f"impacted_case_count={summary.impacted_case_count}")
    print(f"generated_cases={summary.generated_cases}")
    print(f"generated_cases_review={summary.generated_cases_review}")
    print(f"impact_report={summary.impact_report}")
    print(f"impact_review={summary.impact_review}")
    print(f"summary={SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
