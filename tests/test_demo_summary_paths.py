from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_script_module(module_name: str, script_name: str):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


sales_demo = _load_script_module(
    "create_customer_support_faq_change_sales_demo",
    "create_customer_support_faq_change_sales_demo.py",
)
accident_demo = _load_script_module(
    "create_faq_change_accident_demo",
    "create_faq_change_accident_demo.py",
)


def assert_customer_safe_path(value: str) -> None:
    assert not Path(value).is_absolute()
    assert ":\\" not in value
    assert "\\" not in value


def test_sales_demo_phase_summary_uses_relative_artifact_paths(monkeypatch) -> None:
    summary_path = Path("customer_bundle") / "demo_summary.json"
    monkeypatch.setattr(sales_demo, "SUMMARY_PATH", summary_path)

    phase_dir = summary_path.parent / "reports" / "before_stale_v1"
    summary = sales_demo._phase_stats(
        {
            "overall_decision": "ng",
            "decision": {
                "policy_status": "block",
                "metrics": {"overall_pass_rate": 75.0, "s1_pass_rate": 50.0},
            },
            "cases": [{"severity": "S1", "pass_fail": "fail"}],
        },
        phase_dir / "gate-report.md",
        phase_dir / "gate-report.json",
    )

    assert summary.report_path == "reports/before_stale_v1/gate-report.md"
    assert summary.bundle_path == "reports/before_stale_v1/gate-report.json"
    assert_customer_safe_path(summary.report_path)
    assert_customer_safe_path(summary.bundle_path)


def test_accident_demo_summary_paths_are_relative_to_summary(monkeypatch) -> None:
    summary_path = Path("customer_bundle") / "demo_summary.json"
    monkeypatch.setattr(accident_demo, "SUMMARY_JSON", summary_path)

    run_summary = accident_demo.GateRunSummary(
        phase="stale-v1-change-accident",
        exit_code=1,
        status="fail",
        policy_status="block",
        overall_decision="ng",
        report_path=str(summary_path.parent / "02-stale-v1-fail" / "runs" / "gate-report.md"),
        bundle_path=str(summary_path.parent / "02-stale-v1-fail" / "runs" / "gate-report.json"),
    )

    sanitized = accident_demo._sanitize_gate_run_summary(run_summary)

    assert accident_demo._summary_relative_path(summary_path.parent / "cases.csv") == "cases.csv"
    assert sanitized.report_path == "02-stale-v1-fail/runs/gate-report.md"
    assert sanitized.bundle_path == "02-stale-v1-fail/runs/gate-report.json"
    assert_customer_safe_path(sanitized.report_path)
    assert_customer_safe_path(sanitized.bundle_path)
