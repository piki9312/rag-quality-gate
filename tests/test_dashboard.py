from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient


def test_dashboard_routes_render_old_report_fallback_and_monthly_summary(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    pack_dir = workspace / "packs" / "sample-pack"
    runs_dir = workspace / "runs" / "sample-pack"
    pack_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "quality-pack.yml").write_text(
        "\n".join(
            [
                "pack:",
                "  name: sample-pack",
                "  pack_name: sample-pack",
                "  tenant_name: tenant-a",
                "  use_case: hr-faq",
                "  vertical: hr",
                "  risk_profile: high",
                "  owner: ops-team",
                "  environment: poc",
                "  pack_version: '1.0'",
                "  source_pack: demo_cycle",
                "  created_from_template: true",
                "  review_steward: ops-team",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (runs_dir / "gate-report.json").write_text(
        json.dumps(
            {
                "decision": {
                    "run_id": "run-001",
                    "status": "fail",
                    "reasons": ["S1 pass rate: 0.0 < 100.0 (0/1)"],
                    "metrics": {
                        "overall_pass_rate": 40.0,
                        "s1_pass_rate": 0.0,
                        "s1_fail_count": 1.0,
                    },
                    "next_actions": [
                        {
                            "failure_category": "retrieval_miss",
                            "count": 1,
                            "action": "Review retrieval settings",
                            "owner": "T.B.D.",
                            "due": "T.B.D.",
                            "affected_case_ids": ["QA-1"],
                        }
                    ],
                    "judge_fallback_used": True,
                    "judge_fallback_count": 1,
                    "judge_failure_types": {"parse": 1},
                    "judge_reliability": "low",
                    "embedding_fallback_used": False,
                    "embedding_fallback_count": 0,
                    "embedding_fallback_reason": None,
                    "needs_human_review": True,
                    "pack": {
                        "pack_name": "sample-pack",
                        "tenant_name": "tenant-a",
                    },
                    "created_at": "2026-04-22T00:00:00Z",
                },
                "history_summary": {
                    "comparison": {
                        "previous_run_id": "run-000",
                        "current_run_id": "run-001",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (runs_dir / "gate-decisions.jsonl").write_text(
        '{"run_id":"run-001","status":"fail","reasons":["S1 pass rate: 0.0 < 100.0 (0/1)"],"metrics":{"overall_pass_rate":40.0,"s1_pass_rate":0.0,"s1_fail_count":1.0},"next_actions":[],"judge_fallback_used":true,"judge_fallback_count":1,"judge_failure_types":{"parse":1},"judge_reliability":"low","embedding_fallback_used":false,"embedding_fallback_count":0,"embedding_fallback_reason":null,"needs_human_review":true,"pack":{"pack_name":"sample-pack"},"created_at":"2026-04-22T00:00:00Z"}\n',
        encoding="utf-8",
    )
    (runs_dir / "monthly-summary.json").write_text(
        json.dumps(
            {
                "month_start": "2026-04-01",
                "total_runs": 1,
                "blocked_runs": 1,
                "s1_incidents_detected": 1,
                "quality_trend_summary": "Overall pass rate 40.0% -> 40.0%; S1 pass rate 0.0% -> 0.0%; latest status=FAIL",
                "unresolved_issues": ["S1 pass rate: 0.0 < 100.0 (0/1)"],
            }
        ),
        encoding="utf-8",
    )

    from rqg.serving.dashboard import create_dashboard_app

    client = TestClient(create_dashboard_app(workspace_dir=str(workspace)))
    assert client.get("/?lang=ja").status_code == 200
    assert "sample-pack" in client.get("/?lang=ja").text
    assert "tenant-a" in client.get("/packs/sample-pack?lang=ja").text
    assert "run-001" in client.get("/packs/sample-pack/runs?lang=ja").text
    run_detail = client.get("/packs/sample-pack/runs/run-001?lang=ja")
    assert run_detail.status_code == 200
    assert "hero hero--danger" in run_detail.text
    assert "Delivery Review Summary" not in run_detail.text
    assert "S1/S2 Blocking List" not in run_detail.text
    assert "Download Customer Review Markdown" not in run_detail.text
    assert "本番反映不可" in run_detail.text
    assert "この run にはレビュー情報がありません。" in run_detail.text
    assert "判定器信頼度" in run_detail.text
    assert "S1合格率: 0.0 &lt; 100.0 (0/1)" in run_detail.text
    assert "検索漏れ (retrieval_miss)" in run_detail.text
    assert "検索設定や索引対象を見直してください。" in run_detail.text
    assert "顧客提出レポート" in run_detail.text
    assert "未作成" in run_detail.text
    fail_cases = client.get("/packs/sample-pack/fail-cases?lang=ja")
    assert "QA-1" in fail_cases.text
    assert "検索漏れ (retrieval_miss)" in fail_cases.text
    assert "検索設定や索引対象を見直してください。" in fail_cases.text
    monthly = client.get("/packs/sample-pack/monthly?lang=ja")
    assert monthly.status_code == 200
    assert "ブロックrun数" in monthly.text

    english_run_detail = client.get("/packs/sample-pack/runs/run-001?lang=en")
    assert english_run_detail.status_code == 200
    assert "ReviewPacket is not available for this run." in english_run_detail.text
    assert "Delivery Review Summary" not in english_run_detail.text
    assert "Review stage" not in english_run_detail.text
    assert "Production Readiness Card" not in english_run_detail.text


def test_dashboard_global_failures_include_demo_block_and_review() -> None:
    from rqg.serving.dashboard import create_dashboard_app

    client = TestClient(
        create_dashboard_app(
            workspace_dir=".",
            runs_dir="packs/customer_support_pack/reports/demo_runs",
        )
    )

    failures = client.get("/cases/failures?lang=ja")
    assert failures.status_code == 200
    assert "csp-block-refund-202604" in failures.text
    assert "answer_quality_fail" in failures.text
    assert "business_risk" in failures.text
    assert "csp-needs-review-fallback-202604" in failures.text
    assert "evaluator_reliability" in failures.text
    assert "judge_fallback_used" in failures.text


def test_dashboard_run_detail_renders_review_packet_safe_payload(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    runs_dir = workspace / "runs" / "sample-pack"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "gate-report-ci.json").write_text(
        json.dumps(
            {
                "decision": {
                    "run_id": "run-review",
                    "status": "fail",
                    "policy_status": "block",
                    "reasons": ["s1_case_failed"],
                    "metrics": {
                        "overall_pass_rate": 50.0,
                        "s1_pass_rate": 0.0,
                        "s1_fail_count": 1.0,
                    },
                    "next_actions": [],
                    "needs_human_review": True,
                    "pack": {"pack_name": "sample-pack"},
                    "created_at": "2026-05-19T00:00:00Z",
                },
                "review_packet": {
                    "packet_mode": "safe",
                    "review_stage": "post_delivery_change",
                    "run_summary": {
                        "run_id": "run-review",
                        "created_at": "2026-05-19T00:00:00Z",
                        "total_cases": 2,
                        "passed_cases": 1,
                        "failed_cases": 1,
                        "pass_rate": 50.0,
                        "report_mode": "ci",
                    },
                    "decision": {
                        "status": "fail",
                        "policy_status": "block",
                        "customer_status": "No-Go",
                        "needs_human_review": True,
                    },
                    "decision_explanation": {
                        "headline": "No-Go: release should wait.",
                        "decision": "No-Go",
                        "plain_language_reason": "Critical case failed.",
                        "blocking_reasons": [
                            {
                                "reason_code": "s1_case_failed",
                                "label": "Critical case failed",
                                "severity": "Critical",
                                "affected_count": 1,
                                "why_it_blocks": "A high-risk case failed.",
                            }
                        ],
                        "required_actions": ["Fix the critical case and rerun."],
                    },
                    "scope": {
                        "target_name": "",
                        "target_type": "customer_facing_ai",
                        "target_documents": [],
                        "document_versions": [],
                        "change_event": None,
                    },
                    "change_summary": {
                        "change_type": "document_update",
                        "change_id": "",
                        "change_id_hash": "changehash",
                        "changed_assets_count": 1,
                        "affected_documents_count": 1,
                        "affected_business_categories": [],
                        "target_release": "",
                        "change_summary": "Change event metadata is available.",
                        "retest_reason": "Document update can change retrieval evidence.",
                        "changed_assets": [],
                        "affected_documents": [],
                    },
                    "document_corpus": {
                        "document_count": 1,
                        "source_of_truth_type": "approved_policy",
                        "stale_doc_policy": "reject_docs_older_than_30_days",
                        "version_hashes": ["abc123hash"],
                        "has_document_versions": True,
                        "has_source_of_truth": True,
                        "has_stale_doc_policy": True,
                        "target_documents": [],
                        "source_of_truth": "",
                        "affected_business_categories": [],
                        "affected_cases": [],
                    },
                    "severity_summary": {
                        "critical": 1,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    },
                    "risk_breakdown": {
                        "major_misguidance": 0,
                        "evidence_mismatch": 1,
                        "stale_reference": 0,
                        "business_rule_violation": 0,
                        "human_review_required": 1,
                    },
                    "major_failures": [
                        {
                            "failure_id": "failure-abc123",
                            "case_id": "",
                            "case_id_hash": "abc123",
                            "customer_severity": "Critical",
                            "internal_severity": "S1",
                            "failure_category": "evidence_mismatch",
                            "failure_pattern": "",
                            "business_category": "",
                            "go_no_go_impact": "blocks_release",
                            "human_review_required": True,
                            "question_summary": "RAW QUESTION SHOULD NOT RENDER",
                            "expected_summary": "RAW EXPECTED SHOULD NOT RENDER",
                            "actual_summary": "RAW ANSWER SHOULD NOT RENDER",
                            "evidence_status": "mismatch",
                            "safe_reason_code": "evidence_mismatch",
                            "next_action": "Review the evidence alignment.",
                            "suggested_fix": "Align with approved evidence.",
                            "full_detail_ref": "case:abc123",
                        }
                    ],
                    "report_sections": {
                        "executive_summary": "Release should wait.",
                        "decision": "No-Go (block)",
                        "change_summary": "change_type=document_update; affected_documents=1",
                        "scope": "Document corpus: 1 document; has versions=True",
                        "production_readiness": "Not ready for production: 1 blocker.",
                        "major_risks": "1 Critical issue",
                        "blocking_issues": "Critical: evidence_mismatch",
                        "required_actions": "Fix and rerun",
                        "residual_risks": "PASS is scoped.",
                        "disclaimer": "Not a complete guarantee.",
                    },
                    "evidence_policy": {
                        "mode": "safe",
                        "summary": "Safe packet excludes raw text.",
                        "includes_full_evidence": False,
                        "full_evidence_location": "",
                    },
                    "production_readiness": {
                        "status": "not_ready",
                        "blockers": [
                            {
                                "code": "critical_failure_remaining",
                                "label": "Critical failure remains",
                                "reason": "1 Critical failure remains.",
                                "required_action": "Fix and rerun.",
                                "recommended_action": "",
                            }
                        ],
                        "warnings": [
                            {
                                "code": "human_review_required",
                                "label": "Human review is required",
                                "reason": "A human review signal is present.",
                                "required_action": "",
                                "recommended_action": "Complete human review.",
                            }
                        ],
                        "required_actions": ["Fix and rerun.", "Complete human review."],
                        "readiness_summary": "Not ready for production.",
                    },
                    "delivery_review": {
                        "status": "not_deliverable",
                        "summary": "Delivery is not recommended until blockers are fixed.",
                        "unresolved_s1_count": 1,
                        "unresolved_s2_count": 0,
                        "blockers": [
                            {
                                "item_id": "failure-abc123",
                                "severity": "S1",
                                "issue": "evidence_mismatch",
                                "category": "evidence_mismatch",
                                "blocks_delivery": True,
                                "required_action": "Review the evidence alignment.",
                                "owner": "",
                                "due_date": "",
                                "status": "open",
                            }
                        ],
                        "customer_submission_status": "safe_to_share",
                        "required_actions": ["Review the evidence alignment."],
                        "reviewer_notes_placeholder": "Reviewer notes placeholder.",
                    },
                    "blocking_items": [
                        {
                            "item_id": "failure-abc123",
                            "severity": "S1",
                            "issue": "evidence_mismatch",
                            "category": "evidence_mismatch",
                            "blocks_delivery": True,
                            "required_action": "Review the evidence alignment.",
                            "owner": "",
                            "due_date": "",
                            "status": "open",
                        }
                    ],
                    "customer_shareability": {
                        "status": "shareable",
                        "reasons": ["safe_review_packet"],
                        "forbidden_fields_detected": [],
                        "safe_mode_required": True,
                    },
                    "customer_submission_readiness": {
                        "status": "not_recommended",
                        "reasons": ["unresolved_blockers_or_no_go"],
                        "recommendation": "Formal customer submission is not recommended.",
                    },
                    "release_decision": {
                        "decision": "needs_review",
                        "decided_by": "",
                        "decided_at": "",
                        "reviewer_role": "",
                        "accepted_risks": [],
                        "unresolved_blockers": ["failure-abc123"],
                        "required_actions": ["Review the evidence alignment."],
                        "evidence_refs": [],
                        "notes": "",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    from rqg.serving.dashboard import create_dashboard_app

    raw_report = (runs_dir / "gate-report-ci.json").read_text(encoding="utf-8")
    assert '"Critical case failed."' in raw_report
    assert '"Review the evidence alignment."' in raw_report

    client = TestClient(create_dashboard_app(workspace_dir=str(workspace)))
    run_detail = client.get("/runs/run-review?lang=ja")
    assert run_detail.status_code == 200
    assert "hero hero--danger" in run_detail.text
    assert "判定" in run_detail.text
    assert "本番反映不可 (No-Go)" in run_detail.text
    assert "本番移行準備度" in run_detail.text
    assert "本番反映不可です。リリースは見合わせてください。" in run_detail.text
    assert "重大なケースが失敗しています。" in run_detail.text
    assert "重大度サマリー" in run_detail.text
    assert "変更内容" in run_detail.text
    assert "文書更新 (document_update)" in run_detail.text
    assert "safeモードでは変更対象名と影響文書名を展開しません。" in run_detail.text
    assert "根拠文書" in run_detail.text
    assert "本番移行準備度" in run_detail.text
    assert "critical_failure_remaining" in run_detail.text
    assert "重大な失敗が残っています" in run_detail.text
    assert "本番反映前に解消すべき重大な失敗が検出されています。" in run_detail.text
    assert "該当ケースを修正し、再検査してください。" in run_detail.text
    assert "人間レビューが必要です" in run_detail.text
    assert "自動判定だけでは本番反映可否を確定できないケースがあります。" in run_detail.text
    assert "担当者が該当ケースを確認してください。" in run_detail.text
    assert "承認済みポリシー (approved_policy)" in run_detail.text
    assert "reject_docs_older_than_30_days" in run_detail.text
    assert "重大な失敗" in run_detail.text
    assert "失敗内容" in run_detail.text
    assert "影響" in run_detail.text
    assert "Failure Pattern" not in run_detail.text
    assert "Evidence Status" not in run_detail.text
    assert "重大ケースが失敗しました (s1_case_failed)" in run_detail.text
    assert "高リスクのケースが失敗しており、本番反映できません。" in run_detail.text
    assert "重大なケースを修正して再検査してください。" in run_detail.text
    assert "根拠不一致 (evidence_mismatch)" in run_detail.text
    assert "根拠文書に沿って回答を修正し、再検査してください。" in run_detail.text
    assert "本番移行の準備は未完了です。1 件のブロッカーと 1 件の注意事項への対応が必要です。" in run_detail.text
    assert "顧客提出レポートを開く" in run_detail.text
    assert "safeモードでは表示しません" in run_detail.text
    assert "RAW QUESTION SHOULD NOT RENDER" not in run_detail.text
    assert "RAW ANSWER SHOULD NOT RENDER" not in run_detail.text

    customer_review = client.get("/runs/run-review/customer-review.md")
    assert customer_review.status_code == 200
    assert "# Change Impact Quality Review" in customer_review.text
    assert "Review stage: post_delivery_change" in customer_review.text
    assert "Delivery status: not_deliverable" in customer_review.text
    assert "S1: evidence_mismatch" in customer_review.text
    assert "RAW QUESTION SHOULD NOT RENDER" not in customer_review.text
    assert "RAW ANSWER SHOULD NOT RENDER" not in customer_review.text

    failure_detail = client.get("/runs/run-review/failures/failure-abc123?lang=ja")
    assert failure_detail.status_code == 200
    assert "safe版では raw question、answer、evidence はここに表示しません。" in failure_detail.text
    assert "evidence_mismatch" in failure_detail.text
    assert "根拠不一致 (evidence_mismatch)" in failure_detail.text
    assert "根拠文書に沿って回答を修正し、再検査してください。" in failure_detail.text
    assert "RAW EXPECTED SHOULD NOT RENDER" not in failure_detail.text

    report_preview = client.get("/runs/run-review/report-preview?lang=ja")
    assert report_preview.status_code == 200
    assert "report-section" in report_preview.text
    assert "要約" in report_preview.text
    assert "変更概要" in report_preview.text
    assert "リリースは見合わせるべきです。" in report_preview.text
    assert "本番反映不可です。" in report_preview.text
    assert "リリースは見合わせてください。" in report_preview.text
    assert "変更種別は 文書更新 (document_update) です。" in report_preview.text
    assert "再検査理由: 文書更新により検索根拠が変わる可能性があります。" in report_preview.text
    assert "根拠文書は 1 件で、バージョン情報あり=あり です。" in report_preview.text
    assert "本番移行準備度" in report_preview.text
    assert "本番移行準備度は 未準備 (not_ready) です。" in report_preview.text
    assert "重大なケースを修正して再検査してください。" in report_preview.text
    assert "残留リスク: 根拠不一致 (evidence_mismatch)" in report_preview.text
    assert "主なポイント" in report_preview.text

    english_run_detail = client.get("/runs/run-review?lang=en")
    assert english_run_detail.status_code == 200
    assert "hero hero--danger" in english_run_detail.text
    assert "No-Go" in english_run_detail.text
    assert "ReviewPacket is not available for this run." not in english_run_detail.text
    assert "Delivery Review Summary" in english_run_detail.text
    assert "Review stage" in english_run_detail.text
    assert "post_delivery_change" in english_run_detail.text
    assert "Decision Card" in english_run_detail.text
    assert "Production Readiness Card" in english_run_detail.text
    assert "Formal submission readiness" in english_run_detail.text
    assert "not_recommended" in english_run_detail.text
    assert "Critical case failed." in english_run_detail.text
    assert "Review the evidence alignment." in english_run_detail.text
    assert "Failure" in english_run_detail.text
    assert "Impact" in english_run_detail.text

    english_report_preview = client.get("/runs/run-review/report-preview?lang=en")
    assert english_report_preview.status_code == 200
    assert "report-section" in english_report_preview.text
    assert "change_type=document_update" in english_report_preview.text
    assert "Not ready for production: 1 blocker." in english_report_preview.text
