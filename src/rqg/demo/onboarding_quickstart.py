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

import argparse
import json
import os
import shutil
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from rqg.cli import main as cli_main


@dataclass
class QuickstartSummary:
    profile: str
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


@dataclass(frozen=True)
class QuickstartProfileConfig:
    template_pack_dir: Path
    scenario_doc_relpath: Path
    doc_id: str
    title: str
    good_doc: str
    updated_doc: str


REPO_ROOT = Path(__file__).resolve().parents[3]

GOOD_DOC = """# Leave Policy

Paid leave requests must be submitted 5 business days in advance.
Employees should submit the request through the HR system.
"""

UPDATED_DOC = """# Leave Policy

Paid leave requests must be submitted 3 business days in advance.
Employees should submit the request through the HR system.
"""

WIKI_GOOD_DOC = """# VPN Exception FAQ

Temporary VPN exception access requests must be submitted 2 business days in advance.
Employees should submit requests via the service portal.
P1 security incidents must be escalated to the security on-call owner first.
"""

WIKI_UPDATED_DOC = """# VPN Exception FAQ

Temporary VPN exception access requests must be submitted 1 business day in advance.
Employees should submit requests via the service portal.
P1 security incidents must be escalated to the security on-call owner first.
"""


PROFILE_CONFIGS: dict[str, QuickstartProfileConfig] = {
    "demo_cycle": QuickstartProfileConfig(
        template_pack_dir=REPO_ROOT / "packs" / "demo_cycle",
        scenario_doc_relpath=Path("documents/quickstart_policy.md"),
        doc_id="demo-quickstart-policy",
        title="Quickstart Policy",
        good_doc=GOOD_DOC,
        updated_doc=UPDATED_DOC,
    ),
    "hr": QuickstartProfileConfig(
        template_pack_dir=REPO_ROOT / "packs" / "hr",
        scenario_doc_relpath=Path("documents/quickstart_policy.md"),
        doc_id="hr-quickstart-policy",
        title="HR Quickstart Policy",
        good_doc=GOOD_DOC,
        updated_doc=UPDATED_DOC,
    ),
    "wiki": QuickstartProfileConfig(
        template_pack_dir=REPO_ROOT / "packs" / "wiki",
        scenario_doc_relpath=Path("documents/quickstart_policy.md"),
        doc_id="wiki-quickstart-policy",
        title="Wiki Quickstart Policy",
        good_doc=WIKI_GOOD_DOC,
        updated_doc=WIKI_UPDATED_DOC,
    ),
}


def _run_cli(args: list[str], step: str) -> None:
    exit_code = cli_main(args)
    if exit_code != 0:
        raise RuntimeError(f"{step} failed with exit code {exit_code}")


def _prepare_pack(template_pack_dir: Path, work_root: Path, pack_dir: Path) -> None:
    work_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_pack_dir, pack_dir)


def _init_snapshot_from_doc(
    doc_path: Path,
    output_path: Path,
    snapshot_id: str,
    *,
    doc_id: str,
    title: str,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = doc_path.read_text(encoding="utf-8")
    _run_cli(
        [
            "init-snapshot",
            "--snapshot-id",
            snapshot_id,
            "--doc-id",
            doc_id,
            "--title",
            title,
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


def run_demo(profile: str = "demo_cycle") -> tuple[QuickstartSummary, Path]:
    config = PROFILE_CONFIGS[profile]
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    work_root = REPO_ROOT / "demo_runs" / "onboarding_quickstart" / uuid.uuid4().hex[:8]
    pack_dir = work_root / "pack"
    summary_path = work_root / "summary.json"
    doc_path = pack_dir / config.scenario_doc_relpath

    _prepare_pack(config.template_pack_dir, work_root, pack_dir)

    artifacts_dir = work_root / "artifacts"
    index_dir = work_root / "index"
    log_dir = work_root / "runs"
    report_file = log_dir / "gate-report.md"
    decision_file = log_dir / "gate-decision.json"

    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(config.good_doc, encoding="utf-8")

    # 1) ingest
    _run_cli(
        [
            "ingest",
            str(pack_dir / "documents"),
            "--index-dir",
            str(index_dir),
        ],
        step="ingest",
    )

    # Build a stable old snapshot from a copied file to avoid path-overwrite issues.
    old_doc_copy = artifacts_dir / f"{profile}_policy_old.md"
    old_doc_copy.parent.mkdir(parents=True, exist_ok=True)
    old_doc_copy.write_text(config.good_doc, encoding="utf-8")
    old_snapshot = _init_snapshot_from_doc(
        old_doc_copy,
        artifacts_dir / "old_snapshot.json",
        "quickstart-old",
        doc_id=config.doc_id,
        title=config.title,
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
            str(generated_cases),
            "--docs",
            str(pack_dir / "documents"),
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
            str(pack_dir / "gate.yml"),
            "--output-file",
            str(report_file),
            "--decision-file",
            str(decision_file),
        ],
        step="check",
    )

    decision = json.loads(decision_file.read_text(encoding="utf-8"))

    # Prepare updated document and new snapshot for impact.
    doc_path.write_text(config.updated_doc, encoding="utf-8")
    new_doc_copy = artifacts_dir / f"{profile}_policy_new.md"
    new_doc_copy.write_text(config.updated_doc, encoding="utf-8")
    new_snapshot = _init_snapshot_from_doc(
        new_doc_copy,
        artifacts_dir / "new_snapshot.json",
        "quickstart-new",
        doc_id=config.doc_id,
        title=config.title,
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
        profile=profile,
        run_id=work_root.name,
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
    summary_path.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    return summary, summary_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run onboarding quickstart demo flow")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_CONFIGS.keys()),
        default="demo_cycle",
        help="Pack profile used for onboarding quickstart",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary, summary_path = run_demo(profile=args.profile)
    print(f"profile={summary.profile}")
    print(f"run_id={summary.run_id}")
    print(f"gate_status={summary.gate_status}")
    print(f"changed_evidence_count={summary.changed_evidence_count}")
    print(f"impacted_case_count={summary.impacted_case_count}")
    print(f"generated_cases={summary.generated_cases}")
    print(f"generated_cases_review={summary.generated_cases_review}")
    print(f"impact_report={summary.impact_report}")
    print(f"impact_review={summary.impact_review}")
    print(f"summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
