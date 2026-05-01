"""Create deterministic Proof Gate customer-support demo artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from rqg.domain import GateDecision, GateNextAction, GatePackMetadata
from rqg.quality.monthly_summary import (
    build_monthly_summary_payload,
    render_monthly_summary_markdown,
)
from rqg.quality.reporting import GATE_REPORT_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "packs" / "customer_support_pack" / "reports" / "demo_runs"
PACK_DIR = OUTPUT_ROOT / "customer_support_pack"


def main() -> int:
    decisions = [
        _decision_pass(),
        _decision_business_block(),
        _decision_fallback_review(),
    ]
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PACK_DIR.mkdir(parents=True, exist_ok=True)

    for decision in decisions:
        run_dir = OUTPUT_ROOT / decision.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        markdown = _render_markdown(decision)
        history_summary = _history_summary(decision)
        (run_dir / "gate-decision.json").write_text(
            decision.model_dump_json(indent=2),
            encoding="utf-8",
        )
        (run_dir / "gate-report.md").write_text(markdown, encoding="utf-8")
        (run_dir / "gate-report.json").write_text(
            json.dumps(
                {
                    "schema_version": GATE_REPORT_SCHEMA_VERSION,
                    "decision": decision.model_dump(mode="json"),
                    "history_summary": history_summary,
                    "report_markdown": markdown,
                    "artifact_paths": {
                        "report_path": str(run_dir / "gate-report.md"),
                        "decision_path": str(run_dir / "gate-decision.json"),
                        "history_summary_path": str(run_dir / "gate-history-summary.json"),
                        "history_path": str(PACK_DIR / "gate-decisions.jsonl"),
                        "bundle_path": str(run_dir / "gate-report.json"),
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (run_dir / "gate-history-summary.json").write_text(
            json.dumps(history_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    (PACK_DIR / "gate-decisions.jsonl").write_text(
        "".join(decision.model_dump_json() + "\n" for decision in decisions),
        encoding="utf-8",
    )
    monthly = build_monthly_summary_payload(decisions, month="2026-04")
    (PACK_DIR / "monthly-summary.json").write_text(
        json.dumps(monthly, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (PACK_DIR / "monthly-summary.md").write_text(
        render_monthly_summary_markdown(monthly),
        encoding="utf-8",
    )
    return 0


def _pack() -> GatePackMetadata:
    return GatePackMetadata(
        pack_id="customer_support_pack",
        pack_name="Customer Support AI Quality Pack",
        tenant_name="demo_customer",
        use_case="customer_support_faq",
        vertical="customer_support",
        risk_profile="high_external_response",
        environment="demo",
        owner="proofgate-demo",
        pack_version="0.1.0",
        source_pack=None,
        created_from_template=True,
    )


def _decision_pass() -> GateDecision:
    return GateDecision(
        run_id="csp-pass-202604",
        status="pass",
        policy_status="pass",
        reasons=[],
        reason_codes=[],
        metrics={
            "overall_pass_rate": 100.0,
            "s1_pass_rate": 100.0,
            "s1_fail_count": 0.0,
            "current_runs": 10.0,
            "baseline_runs": 0.0,
            "judge_fallback_count": 0.0,
            "embedding_fallback_count": 0.0,
        },
        next_actions=[],
        judge_reliability="high",
        retrieval_reliability="high",
        fallback_summary={
            "judge_fallback_used": False,
            "judge_fallback_count": 0,
            "judge_failure_types": {},
            "embedding_fallback_used": False,
            "embedding_fallback_count": 0,
            "embedding_fallback_reason": None,
            "retrieval_reliability": "high",
        },
        pack=_pack(),
        created_at=datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc),
    )


def _decision_business_block() -> GateDecision:
    return GateDecision(
        run_id="csp-block-refund-202604",
        status="fail",
        policy_status="block",
        reasons=[
            "S1 pass rate: 66.7 < 100.0 (4/6)",
            "Refund policy S1 case failed: digital product refund was incorrectly allowed",
            "This block is caused by business-risk answer quality, not evaluator fallback",
        ],
        reason_codes=["answer_quality_fail", "evidence_mismatch"],
        metrics={
            "overall_pass_rate": 80.0,
            "s1_pass_rate": 66.7,
            "s1_fail_count": 2.0,
            "current_runs": 10.0,
            "baseline_runs": 1.0,
            "judge_fallback_count": 0.0,
            "embedding_fallback_count": 0.0,
        },
        next_actions=[
            GateNextAction(
                failure_category="answer_quality_fail",
                count=2,
                action="Fix refund and cancellation answers, then rerun the gate before customer release",
                owner="support_quality_owner",
                due="before-release",
                affected_case_ids=["CS-S1-REFUND-001", "CS-S1-CANCEL-001"],
            )
        ],
        judge_reliability="high",
        retrieval_reliability="high",
        fallback_summary={
            "judge_fallback_used": False,
            "judge_fallback_count": 0,
            "judge_failure_types": {},
            "embedding_fallback_used": False,
            "embedding_fallback_count": 0,
            "embedding_fallback_reason": None,
            "retrieval_reliability": "high",
            "block_origin": "business_risk",
        },
        pack=_pack(),
        created_at=datetime(2026, 4, 8, 9, 0, tzinfo=timezone.utc),
    )


def _decision_fallback_review() -> GateDecision:
    return GateDecision(
        run_id="csp-needs-review-fallback-202604",
        status="pass",
        policy_status="needs_human_review",
        reasons=[
            "Judge fallback detected; re-run evaluation and verify judge/API connectivity before release",
            "Human review required because run reliability signals were degraded",
            "This review state is caused by evaluator reliability, not a confirmed business-rule violation",
        ],
        reason_codes=["judge_fallback_used", "judge_unreliable", "needs_human_review"],
        metrics={
            "overall_pass_rate": 100.0,
            "s1_pass_rate": 100.0,
            "s1_fail_count": 0.0,
            "current_runs": 10.0,
            "baseline_runs": 2.0,
            "judge_fallback_count": 1.0,
            "embedding_fallback_count": 0.0,
        },
        next_actions=[
            GateNextAction(
                failure_category="judge_fallback_used",
                count=1,
                action="Re-run judge-enabled evaluation and route this run to the quality owner if fallback repeats",
                owner="proofgate-demo",
                due="same-day",
                affected_case_ids=["CS-S1-TERMS-001"],
            )
        ],
        judge_fallback_used=True,
        judge_fallback_count=1,
        judge_failure_types={"provider_error": 1},
        judge_reliability="low",
        retrieval_reliability="high",
        needs_human_review=True,
        fallback_summary={
            "judge_fallback_used": True,
            "judge_fallback_count": 1,
            "judge_failure_types": {"provider_error": 1},
            "embedding_fallback_used": False,
            "embedding_fallback_count": 0,
            "embedding_fallback_reason": None,
            "retrieval_reliability": "high",
            "block_origin": "evaluator_reliability",
        },
        approval={
            "approval_required": True,
            "approval_status": "pending",
            "approver_role": "quality_owner",
        },
        pack=_pack(),
        created_at=datetime(2026, 4, 15, 9, 0, tzinfo=timezone.utc),
    )


def _render_markdown(decision: GateDecision) -> str:
    fallback_used = decision.judge_fallback_used or decision.embedding_fallback_used
    actions = "\n".join(
        f"- {action.failure_category}: {action.action}" for action in decision.next_actions
    )
    return (
        f"## Proof Gate Demo Run: {decision.policy_status.upper()}\n\n"
        f"- Run ID: {decision.run_id}\n"
        f"- Pack: {decision.pack.pack_name if decision.pack else 'customer_support_pack'}\n"
        f"- Legacy status: {decision.status.upper()}\n"
        f"- Policy status: {decision.policy_status.upper()}\n"
        f"- S1 fail count: {int(decision.metrics.get('s1_fail_count', 0))}\n"
        f"- Judge reliability: {decision.judge_reliability.upper()}\n"
        f"- Fallback used: {'YES' if fallback_used else 'NO'}\n\n"
        "### Reasons\n\n"
        + ("\n".join(f"- {reason}" for reason in decision.reasons) or "- None")
        + "\n\n### Next Actions\n\n"
        + (actions or "- No immediate action required.")
        + "\n"
    )


def _history_summary(decision: GateDecision) -> dict[str, object]:
    return {
        "entries": 1,
        "status_mix": {
            "pass": 1 if decision.status == "pass" else 0,
            "warn": 1 if decision.status == "warn" else 0,
            "fail": 1 if decision.status == "fail" else 0,
        },
        "week_start": "2026-03-30",
        "compare_offset": 1,
        "trend_window": 5,
        "summary_lines": [
            f"- Latest status: {decision.status.upper()} ({decision.run_id})",
            f"- Policy status: {decision.policy_status.upper()}",
            f"- Judge reliability: {decision.judge_reliability.upper()}",
        ],
        "trend": {
            "latest_run_id": decision.run_id,
            "latest_status": decision.status.upper(),
            "streak_count": 1,
            "status_sequence": [decision.status.upper()],
            "metric_deltas": [],
            "window_size": 1,
        },
        "comparison": None,
        "failure_action_coverage": None,
        "uncovered_categories": [],
        "stale_case_review": None,
        "reliability": {
            "judge_fallback_used": decision.judge_fallback_used,
            "judge_fallback_count": decision.judge_fallback_count,
            "judge_failure_types": decision.judge_failure_types,
            "judge_reliability": decision.judge_reliability,
            "embedding_fallback_used": decision.embedding_fallback_used,
            "embedding_fallback_count": decision.embedding_fallback_count,
            "embedding_fallback_reason": decision.embedding_fallback_reason,
            "retrieval_reliability": decision.retrieval_reliability,
            "fallback_summary": decision.fallback_summary,
            "policy_status": decision.policy_status,
            "needs_human_review": decision.needs_human_review,
        },
        "review_steward": "proofgate-demo",
    }


if __name__ == "__main__":
    raise SystemExit(main())
