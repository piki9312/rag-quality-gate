"""Create a minimal before/after sales demo for FAQ v1 -> v2 change accidents."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from rqg.cli import main as cli_main
from rqg.quality.poc_set import build_case_set_summary, load_poc_candidates

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "packs" / "customer_support_pack"
DEMO_ROOT = ROOT / "demos" / "customer_support_faq_change"
SOURCE_CASES = DEMO_ROOT / "generated_cases.csv"
ROOT_CASES = DEMO_ROOT / "cases.csv"
ROOT_CASE_SET_SUMMARY = DEMO_ROOT / "case_set_summary.json"
SOURCE_V1 = DEMO_ROOT / "demo_faq_v1.md"
SOURCE_V2 = DEMO_ROOT / "demo_faq_v2.md"
REPORTS_DIR = DEMO_ROOT / "reports"
BEFORE_DIR = REPORTS_DIR / "before_stale_v1"
AFTER_DIR = REPORTS_DIR / "after_v2_reference"
SUMMARY_PATH = DEMO_ROOT / "demo_summary.json"


@dataclass(frozen=True)
class PhaseSummary:
    overall_decision: str
    policy_status: str
    overall_pass_rate: float
    s1_pass_rate: float
    s1_failures: int
    report_path: str
    bundle_path: str


@dataclass(frozen=True)
class DemoSummary:
    before: PhaseSummary
    after: PhaseSummary
    representative_s1_failure: dict[str, object]
    key_message: str


def _reset_phase_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _materialize_demo_case_set() -> Path:
    DEMO_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_CASES, ROOT_CASES)
    candidates = load_poc_candidates(SOURCE_CASES, source_type="generated")
    summary = build_case_set_summary(candidates, warnings=[])
    ROOT_CASE_SET_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return ROOT_CASES


def _phase_stats(bundle: dict[str, object], report_path: Path, bundle_path: Path) -> PhaseSummary:
    decision = dict(bundle.get("decision") or {})
    summary = dict(bundle.get("summary") or {})
    cases = list(bundle.get("cases") or [])
    overall_pass_rate = float(summary.get("overall_pass_rate") or decision.get("metrics", {}).get("overall_pass_rate") or 0.0)
    s1_pass_rate = float(summary.get("s1_pass_rate") or decision.get("metrics", {}).get("s1_pass_rate") or 0.0)
    s1_failures = sum(
        1
        for item in cases
        if str(item.get("severity") or "").upper() == "S1" and item.get("pass_fail") == "fail"
    )
    return PhaseSummary(
        overall_decision=str(bundle.get("overall_decision") or ""),
        policy_status=str(decision.get("policy_status") or "").upper(),
        overall_pass_rate=overall_pass_rate,
        s1_pass_rate=s1_pass_rate,
        s1_failures=s1_failures,
        report_path=str(report_path),
        bundle_path=str(bundle_path),
    )


def _representative_s1_failure(bundle: dict[str, object]) -> dict[str, object]:
    for item in list(bundle.get("cases") or []):
        if item.get("pass_fail") != "fail":
            continue
        if str(item.get("severity") or "").upper() != "S1":
            continue
        if str(item.get("risk_domain") or "") not in {"refund", "cancellation"}:
            continue
        return {
            "case_id": item.get("case_id"),
            "question": item.get("question"),
            "ai_answer": item.get("ai_answer"),
            "fail_reason": item.get("fail_reason"),
            "risk_domain": item.get("risk_domain"),
        }
    raise RuntimeError("No representative refund/cancellation S1 failure found in before bundle")


def _run_phase(phase_dir: Path, faq_doc: Path) -> tuple[dict[str, object], int]:
    report_path = phase_dir / "gate-report.md"
    bundle_path = phase_dir / "gate-report.json"

    tmp_parent = ROOT / ".tmp"
    tmp_parent.mkdir(parents=True, exist_ok=True)
    tmp = tmp_parent / f"sales_demo_{phase_dir.name}_{uuid.uuid4().hex}"
    docs_dir = tmp / "documents"
    index_dir = tmp / "index"
    log_dir = tmp / "gate_logs"
    decision_path = tmp / "gate-decision.json"
    docs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(faq_doc, docs_dir / "demo_faq.md")

    exit_code = cli_main(
        [
            "gate",
            str(ROOT_CASES),
            "--pack",
            str(PACK_DIR),
            "--docs",
            str(docs_dir),
            "--index-dir",
            str(index_dir),
            "--log-dir",
            str(log_dir),
            "--output-file",
            str(report_path),
            "--bundle-file",
            str(bundle_path),
            "--decision-file",
            str(decision_path),
            "--mock",
            "--reset-log-dir",
        ]
    )

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    return bundle, exit_code


def run_demo() -> DemoSummary:
    _materialize_demo_case_set()
    _reset_phase_dir(BEFORE_DIR)
    _reset_phase_dir(AFTER_DIR)

    before_bundle, before_exit = _run_phase(BEFORE_DIR, SOURCE_V1)
    after_bundle, after_exit = _run_phase(AFTER_DIR, SOURCE_V2)

    before = _phase_stats(
        before_bundle,
        BEFORE_DIR / "gate-report.md",
        BEFORE_DIR / "gate-report.json",
    )
    after = _phase_stats(
        after_bundle,
        AFTER_DIR / "gate-report.md",
        AFTER_DIR / "gate-report.json",
    )

    if before.overall_decision != "ng" or before.policy_status != "BLOCK":
        raise RuntimeError(
            f"Expected before phase to be NG/BLOCK, got {before.overall_decision}/{before.policy_status}"
        )
    if after.overall_decision not in {"ok", "needs_confirmation"}:
        raise RuntimeError(
            f"Expected after phase to be OK or needs_confirmation, got {after.overall_decision}"
        )
    if after.policy_status not in {"PASS", "WARN", "NEEDS_HUMAN_REVIEW"}:
        raise RuntimeError(
            f"Expected after policy status to be PASS/WARN/NEEDS_HUMAN_REVIEW, got {after.policy_status}"
        )
    if after.s1_failures > before.s1_failures:
        raise RuntimeError("After phase unexpectedly increased S1 failures")
    if after_exit not in {0, 1} or before_exit not in {0, 1}:
        raise RuntimeError("Unexpected gate exit code while creating sales demo")

    summary = DemoSummary(
        before=before,
        after=after,
        representative_s1_failure=_representative_s1_failure(before_bundle),
        key_message=(
            "FAQ変更後に古い回答が残る事故をProof GateがS1重大失敗として検知し、"
            "修正後のv2 reference runでS1失敗の解消とGate改善を確認できる。"
        ),
    )
    SUMMARY_PATH.write_text(json.dumps(asdict(summary), indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> int:
    summary = run_demo()
    print(f"before_overall_decision={summary.before.overall_decision}")
    print(f"before_policy_status={summary.before.policy_status}")
    print(f"after_overall_decision={summary.after.overall_decision}")
    print(f"after_policy_status={summary.after.policy_status}")
    print(f"before_s1_pass_rate={summary.before.s1_pass_rate}")
    print(f"after_s1_pass_rate={summary.after.s1_pass_rate}")
    print(f"representative_s1_failure={summary.representative_s1_failure.get('case_id')}")
    print(f"summary={SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
