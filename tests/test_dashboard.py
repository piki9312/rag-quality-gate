from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient


def test_dashboard_routes_render_pack_runs_and_monthly_summary(tmp_path: Path) -> None:
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
    assert client.get("/").status_code == 200
    assert "sample-pack" in client.get("/").text
    assert "tenant-a" in client.get("/packs/sample-pack").text
    assert "run-001" in client.get("/packs/sample-pack/runs").text
    run_detail = client.get("/packs/sample-pack/runs/run-001")
    assert run_detail.status_code == 200
    assert "Judge reliability" in run_detail.text
    fail_cases = client.get("/packs/sample-pack/fail-cases")
    assert "QA-1" in fail_cases.text
    monthly = client.get("/packs/sample-pack/monthly")
    assert monthly.status_code == 200
    assert "Blocked runs" in monthly.text


def test_dashboard_global_failures_include_demo_block_and_review() -> None:
    from rqg.serving.dashboard import create_dashboard_app

    client = TestClient(
        create_dashboard_app(
            workspace_dir=".",
            runs_dir="packs/customer_support_pack/reports/demo_runs",
        )
    )

    failures = client.get("/cases/failures")
    assert failures.status_code == 200
    assert "csp-block-refund-202604" in failures.text
    assert "answer_quality_fail" in failures.text
    assert "business_risk" in failures.text
    assert "csp-needs-review-fallback-202604" in failures.text
    assert "evaluator_reliability" in failures.text
    assert "judge_fallback_used" in failures.text
