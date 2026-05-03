"""Create deterministic FAQ v1 -> v2 change-accident demo artifacts."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from rqg.casegen import generate_eval_cases_from_snapshot, write_review_output
from rqg.cli import main as cli_main
from rqg.cli.helpers import load_snapshot_from_file
from rqg.quality.case_merge import load_csv_rows
from rqg.quality.poc_set import build_case_set_summary, load_poc_candidates, write_poc_cases_csv
from rqg.quality.reporting import safe_relative_artifact_path

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "packs" / "customer_support_pack"
DEMO_DOCS_DIR = ROOT / "demos" / "customer_support_faq_change"
V1_DOC = DEMO_DOCS_DIR / "demo_faq_v1.md"
V2_DOC = DEMO_DOCS_DIR / "demo_faq_v2.md"
WORK_ROOT = ROOT / "demo_runs" / "faq_change_accident"

CASEGEN_DIR = WORK_ROOT / "casegen_input"
CASEGEN_DOC = CASEGEN_DIR / "demo_faq.md"
SNAPSHOT_JSON = CASEGEN_DIR / "demo_faq_v2_snapshot.json"
RAW_GENERATED_JSON = WORK_ROOT / "generated_eval_cases.json"
RAW_REVIEW_CSV = WORK_ROOT / "generated_eval_cases_review.csv"
GENERATED_CASES_CSV = WORK_ROOT / "generated_cases.csv"
POC_CASES_CSV = WORK_ROOT / "cases.csv"
CASE_SET_SUMMARY_JSON = WORK_ROOT / "case_set_summary.json"
SUMMARY_JSON = WORK_ROOT / "demo_summary.json"

PASS_DIR = WORK_ROOT / "01-v2-reference"
FAIL_DIR = WORK_ROOT / "02-stale-v1-fail"
TODAY = "2026-05-01"


@dataclass(frozen=True)
class GeneratedCaseSpec:
    risk_domain: str
    question: str
    expected_keywords: tuple[str, ...]
    selection_band: str
    required_action: str


@dataclass(frozen=True)
class GateRunSummary:
    phase: str
    exit_code: int
    status: str
    policy_status: str
    overall_decision: str
    report_path: str
    bundle_path: str


@dataclass(frozen=True)
class DemoSummary:
    work_root: str
    generated_cases: str
    generated_case_count: int
    poc_cases: str
    case_set_summary: str
    risk_domain_mix: dict[str, int]
    reference_gate: GateRunSummary
    stale_change_gate: GateRunSummary
    representative_s1_failure: dict[str, object]


SECTION_SPECS: dict[str, GeneratedCaseSpec] = {
    "Campaign refund window": GeneratedCaseSpec(
        risk_domain="refund",
        question="Can I get a refund within 7 days?",
        expected_keywords=(
            "campaign tagged products",
            "within 7 days",
            "standard products are not refundable",
        ),
        selection_band="S1",
        required_action="block",
    ),
    "Standard product refund scope": GeneratedCaseSpec(
        risk_domain="refund",
        question="Can I get a normal refund for a standard product?",
        expected_keywords=(
            "standard product refund requests are not approved",
            "legal defect review",
            "must not promise a normal refund",
        ),
        selection_band="S1",
        required_action="block",
    ),
    "Refund exception review": GeneratedCaseSpec(
        risk_domain="refund",
        question="Can the AI approve an exceptional refund on its own?",
        expected_keywords=(
            "human billing review only",
            "AI must not approve",
            "exceptional refunds",
        ),
        selection_band="S1",
        required_action="needs_human_review",
    ),
    "Chargeback and refund overlap": GeneratedCaseSpec(
        risk_domain="refund",
        question="Can I open a chargeback and still expect a normal refund flow?",
        expected_keywords=(
            "refund review is paused",
            "must not promise both paths",
            "contact support before opening a chargeback",
        ),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
    "Monthly cancellation timing": GeneratedCaseSpec(
        risk_domain="cancellation",
        question="If I cancel now does billing stop today?",
        expected_keywords=(
            "next renewal date",
            "does not stop billing on the same day",
            "cancellation requests may be submitted at any time",
        ),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
    "Free-trial cancellation": GeneratedCaseSpec(
        risk_domain="cancellation",
        question="If I cancel during the free trial will I still be charged?",
        expected_keywords=(
            "before the trial ends",
            "prevent paid conversion",
            "cannot reverse a paid conversion automatically",
        ),
        selection_band="S1",
        required_action="block",
    ),
    "Mid-term annual cancellation": GeneratedCaseSpec(
        risk_domain="cancellation",
        question="If I cancel mid-term can the remaining annual charge be waived?",
        expected_keywords=(
            "stops the next renewal only",
            "remaining contract charges are not waived",
            "manual exception is approved",
        ),
        selection_band="S1",
        required_action="block",
    ),
    "Cancellation confirmation record": GeneratedCaseSpec(
        risk_domain="cancellation",
        question="What should I keep after cancellation?",
        expected_keywords=(
            "cancellation confirmation email",
            "screenshot",
            "order record",
        ),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
    "Post-cancellation data retention": GeneratedCaseSpec(
        risk_domain="cancellation",
        question="How long is customer data kept after cancellation?",
        expected_keywords=(
            "data retention after cancellation",
            "published account policy",
            "documented retention window",
        ),
        selection_band="S3",
        required_action="allow_with_warning",
    ),
    "Plan price display": GeneratedCaseSpec(
        risk_domain="pricing",
        question="Where are current plan prices shown?",
        expected_keywords=(
            "pricing page",
            "current billing currency",
            "plan prices",
        ),
        selection_band="S3",
        required_action="allow_with_warning",
    ),
    "Annual discount disclosure": GeneratedCaseSpec(
        risk_domain="pricing",
        question="Is the annual plan discount a standard promise?",
        expected_keywords=(
            "published annual plan page",
            "must not promise a discount",
            "current offer",
        ),
        selection_band="S3",
        required_action="allow_with_warning",
    ),
    "Invoice download": GeneratedCaseSpec(
        risk_domain="pricing",
        question="Where can I download invoices?",
        expected_keywords=(
            "billing portal",
            "account owner",
            "invoices are available",
        ),
        selection_band="S3",
        required_action="allow_with_warning",
    ),
    "Tax display": GeneratedCaseSpec(
        risk_domain="pricing",
        question="Are prices shown with or without tax?",
        expected_keywords=(
            "tax inclusion depends on the current billing page",
            "customer region",
            "check that page",
        ),
        selection_band="S3",
        required_action="allow_with_warning",
    ),
    "Auto-renewal notice": GeneratedCaseSpec(
        risk_domain="contract",
        question="When is the renewal notice sent?",
        expected_keywords=(
            "30 days before renewal",
            "active contracts",
            "auto renewal notices",
        ),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
    "Contract owner change": GeneratedCaseSpec(
        risk_domain="contract",
        question="How do I change the contract owner?",
        expected_keywords=(
            "support",
            "current owner approval",
            "verification",
        ),
        selection_band="S3",
        required_action="allow_with_warning",
    ),
    "Contract amendment timing": GeneratedCaseSpec(
        risk_domain="contract",
        question="Can a contract amendment be applied mid-term?",
        expected_keywords=(
            "mid term",
            "support review",
            "written confirmation",
        ),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
    "Billing dispute deadline": GeneratedCaseSpec(
        risk_domain="deadline_procedure",
        question="How soon must a billing dispute be submitted?",
        expected_keywords=(
            "5 business days",
            "invoice date",
            "billing dispute requests",
        ),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
    "Incorrect charge review path": GeneratedCaseSpec(
        risk_domain="deadline_procedure",
        question="How should an incorrect charge be reviewed?",
        expected_keywords=(
            "billing support form",
            "order ID",
            "screenshot",
        ),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
    "Support contact channel": GeneratedCaseSpec(
        risk_domain="general_faq",
        question="How can customers contact support?",
        expected_keywords=(
            "help center chat",
            "email form",
            "published support hours",
        ),
        selection_band="S3",
        required_action="allow_with_warning",
    ),
    "Payment incident escalation": GeneratedCaseSpec(
        risk_domain="deadline_procedure",
        question="Who should be contacted first for a payment incident?",
        expected_keywords=(
            "2 business days",
            "billing risk desk first",
            "support second",
        ),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
}

# Keep this script aligned with demos/customer_support_faq_change/demo_faq_v2.md.
# S3 remains a PoC selection band only; runtime cases.csv still emits S1/S2.
SECTION_SPECS = {
    "Campaign refund": GeneratedCaseSpec(
        risk_domain="refund",
        question="キャンペーン商品は購入から7日以内なら返金できますか。",
        expected_keywords=(
            "キャンペーン対象商品",
            "購入から7日以内",
            "通常商品は通常返金の対象外",
        ),
        selection_band="S1",
        required_action="block",
    ),
    "Trial cancellation": GeneratedCaseSpec(
        risk_domain="cancellation",
        question="無料トライアル中に解約すれば課金されませんか。",
        expected_keywords=(
            "トライアル終了前",
            "課金開始後の自動取消はできません",
            "有料化を防ぐ",
        ),
        selection_band="S1",
        required_action="block",
    ),
    "Auto renewal": GeneratedCaseSpec(
        risk_domain="contract",
        question="年額契約の自動更新通知はいつ送られますか。",
        expected_keywords=(
            "更新日の30日前",
            "自動更新通知",
            "メールで送られます",
        ),
        selection_band="S1",
        required_action="block",
    ),
    "Pricing page": GeneratedCaseSpec(
        risk_domain="pricing",
        question="現在のプラン料金はどこで確認できますか。",
        expected_keywords=("料金ページ", "請求通貨", "同じ画面"),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
    "Data retention": GeneratedCaseSpec(
        risk_domain="general_faq",
        question="解約後のデータはしばらく残りますか。",
        expected_keywords=("公開中のアカウントポリシー", "文書化された保持期間", "データ保持"),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
    "Contract change": GeneratedCaseSpec(
        risk_domain="contract",
        question="契約内容の変更は契約期間中でも反映できますか。",
        expected_keywords=("サポート審査", "書面確認", "契約期間中"),
        selection_band="S2",
        required_action="allow_with_warning",
    ),
}

EVIDENCE_ID_BY_HEADING = {
    "Campaign refund": "demo_faq.md#campaign-refund",
    "Trial cancellation": "demo_faq.md#trial-cancel",
    "Auto renewal": "demo_faq.md#auto-renewal",
    "Pricing page": "",
    "Data retention": "demo_faq.md#data-retention",
    "Contract change": "demo_faq.md#contract-change",
}


def _reset_work_root() -> None:
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    WORK_ROOT.mkdir(parents=True, exist_ok=True)


def _stage_casegen_source() -> None:
    CASEGEN_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(V2_DOC, CASEGEN_DOC)


def _init_snapshot() -> None:
    content = CASEGEN_DOC.read_text(encoding="utf-8")
    exit_code = cli_main(
        [
            "init-snapshot",
            "--snapshot-id",
            "faq-change-demo-v2",
            "--doc-id",
            "demo_faq.md",
            "--title",
            "Customer Support FAQ",
            "--source-path",
            "demo_faq.md",
            "--content",
            content,
            "--output",
            str(SNAPSHOT_JSON),
        ]
    )
    if exit_code != 0:
        raise RuntimeError("Failed to initialize v2 snapshot JSON")


def _generate_formal_rows() -> list[dict[str, str]]:
    snapshot = load_snapshot_from_file(SNAPSHOT_JSON)
    bundle = generate_eval_cases_from_snapshot(
        snapshot,
        snapshot_path=SNAPSHOT_JSON,
        mode="rule",
        max_cases=200,
        use_llm=False,
    )

    RAW_GENERATED_JSON.write_text(
        json.dumps([case.model_dump(mode="json") for case in bundle.cases], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_review_output(RAW_REVIEW_CSV, bundle.cases)

    section_by_id = {section.section_id: section for section in bundle.sections}
    rows: list[dict[str, str]] = []
    seen_sections: set[str] = set()
    covered_headings: set[str] = set()

    for case in bundle.cases:
        if not case.expected_evidence:
            continue
        section_id = case.expected_evidence[0]
        if section_id in seen_sections:
            continue
        section = section_by_id[section_id]
        heading = section.heading.strip()
        spec = SECTION_SPECS.get(heading)
        if spec is None:
            continue
        seen_sections.add(section_id)
        covered_headings.add(heading)
        rows.append(_build_generated_row(case.case_id, section_id, heading, spec))

    missing = sorted(set(SECTION_SPECS) - covered_headings)
    if missing:
        raise RuntimeError("Missing generated sections for headings: " + ", ".join(missing))
    if len(rows) < len(SECTION_SPECS):
        raise RuntimeError(
            f"Expected at least {len(SECTION_SPECS)} generated cases, got {len(rows)}"
        )

    return rows


def _build_generated_row(
    case_id: str,
    section_id: str,
    heading: str,
    spec: GeneratedCaseSpec,
) -> dict[str, str]:
    evidence_id = EVIDENCE_ID_BY_HEADING.get(heading, section_id)
    severity = "S1" if spec.selection_band == "S1" else "S2"
    owner_role = "support_quality_owner" if spec.selection_band == "S1" else "support_ops"
    min_case_score = "100" if spec.selection_band == "S1" else "85"
    notes = ";".join(
        [
            "source_type:generated",
            "generator:casegen_rule",
            f"section_id:{section_id}",
            f"evidence_id:{evidence_id}",
            "demo_source:demo_faq_v2.md",
            f"poc_band:{spec.selection_band}",
            f"expected_decision:{spec.required_action}",
        ]
    )
    return {
        "case_id": case_id,
        "name": heading,
        "status": "active",
        "severity": severity,
        "eval_mode": "evidence_keyword",
        "question": spec.question,
        "expected_answer": "",
        "expected_evidence": evidence_id,
        "expected_keywords": ";".join(spec.expected_keywords),
        "category": spec.risk_domain,
        "risk_domain": spec.risk_domain,
        "required_action": spec.required_action,
        "evidence_required": "true" if evidence_id else "false",
        "owner_role": owner_role,
        "source_doc": "demo_faq.md",
        "owner": "proofgate-demo",
        "min_case_score": min_case_score,
        "updated_at": TODAY,
        "last_reviewed_at": TODAY,
        "notes": notes,
    }


def _build_poc_case_set() -> None:
    rows = load_csv_rows(GENERATED_CASES_CSV)
    write_poc_cases_csv(POC_CASES_CSV, rows)
    candidates = load_poc_candidates(GENERATED_CASES_CSV, source_type="generated")
    summary = build_case_set_summary(candidates, warnings=[])
    CASE_SET_SUMMARY_JSON.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _prepare_docs(phase_dir: Path, demo_doc: Path) -> Path:
    docs_dir = phase_dir / "documents"
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    shutil.copytree(PACK_DIR / "documents", docs_dir)
    shutil.copy2(demo_doc, docs_dir / "demo_faq.md")
    return docs_dir


def _run_gate_phase(phase_dir: Path, demo_doc: Path, phase_name: str) -> GateRunSummary:
    phase_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = _prepare_docs(phase_dir, demo_doc)
    index_dir = phase_dir / "index"
    log_dir = phase_dir / "runs"
    report_path = log_dir / "gate-report.md"
    decision_path = log_dir / "gate-decision.json"
    bundle_path = log_dir / "gate-report.json"

    exit_code = cli_main(
        [
            "gate",
            str(POC_CASES_CSV),
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
            "--decision-file",
            str(decision_path),
            "--bundle-file",
            str(bundle_path),
            "--mock",
            "--reset-log-dir",
        ]
    )

    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    return GateRunSummary(
        phase=phase_name,
        exit_code=exit_code,
        status=str(decision.get("status", "")),
        policy_status=str(decision.get("policy_status", "")),
        overall_decision=str(bundle.get("overall_decision", "")),
        report_path=str(report_path),
        bundle_path=str(bundle_path),
    )


def _extract_representative_s1_failure(bundle_path: str | Path) -> dict[str, object]:
    bundle = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    cases = list(bundle.get("cases") or [])
    def _serialize(item: dict[str, object]) -> dict[str, object]:
        return {
            "case_id": item.get("case_id"),
            "question": item.get("question"),
            "ai_answer": item.get("ai_answer"),
            "fail_reason": item.get("fail_reason"),
            "risk_domain": item.get("risk_domain"),
        }

    preferred: list[dict[str, object]] = []
    fallback: list[dict[str, object]] = []
    for item in cases:
        if item.get("severity") != "S1" or item.get("pass_fail") != "fail":
            continue
        case_id = str(item.get("case_id") or "")
        risk_domain = str(item.get("risk_domain") or "")
        if case_id.startswith("customer_support_faq_") and risk_domain in {"refund", "cancellation"}:
            preferred.append(item)
        else:
            fallback.append(item)

    if preferred:
        return _serialize(preferred[0])
    if fallback:
        return _serialize(fallback[0])
    raise RuntimeError("No S1 failing case found in stale-change gate report")


def _summary_relative_path(path: str | Path) -> str:
    return safe_relative_artifact_path(path, SUMMARY_JSON.parent)


def _sanitize_gate_run_summary(summary: GateRunSummary) -> GateRunSummary:
    return GateRunSummary(
        phase=summary.phase,
        exit_code=summary.exit_code,
        status=summary.status,
        policy_status=summary.policy_status,
        overall_decision=summary.overall_decision,
        report_path=_summary_relative_path(summary.report_path),
        bundle_path=_summary_relative_path(summary.bundle_path),
    )


def run_demo() -> DemoSummary:
    _reset_work_root()
    _stage_casegen_source()
    _init_snapshot()

    generated_rows = _generate_formal_rows()
    write_poc_cases_csv(GENERATED_CASES_CSV, generated_rows)
    _build_poc_case_set()

    case_set_summary = json.loads(CASE_SET_SUMMARY_JSON.read_text(encoding="utf-8"))

    reference_gate = _run_gate_phase(PASS_DIR, V2_DOC, "v2-reference")

    stale_change_gate = _run_gate_phase(FAIL_DIR, V1_DOC, "stale-v1-change-accident")
    if stale_change_gate.policy_status not in {"block", "needs_human_review"}:
        raise RuntimeError(
            "Expected stale v1 gate to be blocked or sent to review, got "
            f"{stale_change_gate.policy_status}"
        )
    if stale_change_gate.overall_decision not in {"ng", "needs_confirmation"}:
        raise RuntimeError(
            f"Expected stale v1 overall decision to be NG/needs_confirmation, got {stale_change_gate.overall_decision}"
        )

    representative_s1_failure = _extract_representative_s1_failure(stale_change_gate.bundle_path)
    summary = DemoSummary(
        work_root=_summary_relative_path(WORK_ROOT),
        generated_cases=_summary_relative_path(GENERATED_CASES_CSV),
        generated_case_count=len(generated_rows),
        poc_cases=_summary_relative_path(POC_CASES_CSV),
        case_set_summary=_summary_relative_path(CASE_SET_SUMMARY_JSON),
        risk_domain_mix=dict(case_set_summary.get("risk_domain_mix") or {}),
        reference_gate=_sanitize_gate_run_summary(reference_gate),
        stale_change_gate=_sanitize_gate_run_summary(stale_change_gate),
        representative_s1_failure=representative_s1_failure,
    )
    SUMMARY_JSON.write_text(json.dumps(asdict(summary), indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def main() -> int:
    summary = run_demo()
    print(f"generated_cases={summary.generated_cases}")
    print(f"generated_case_count={summary.generated_case_count}")
    print(f"case_set_summary={summary.case_set_summary}")
    print(f"reference_policy_status={summary.reference_gate.policy_status}")
    print(f"stale_change_policy_status={summary.stale_change_gate.policy_status}")
    print(f"stale_change_overall_decision={summary.stale_change_gate.overall_decision}")
    print(f"representative_s1_failure={summary.representative_s1_failure.get('case_id')}")
    print(f"summary={SUMMARY_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
