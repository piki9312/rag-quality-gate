from __future__ import annotations

import re
from pathlib import Path

TEMPLATE_ROOT = Path("templates/customer-rqg-template")
REVIEWS_ROOT = TEMPLATE_ROOT / "reviews"
MONTHLY_GATE_WORKFLOW = TEMPLATE_ROOT / ".github" / "workflows" / "monthly-gate.yml"


def test_customer_template_reviews_files_exist() -> None:
    expected_paths = [
        REVIEWS_ROOT / "README.md",
        REVIEWS_ROOT / "gate_reviews" / ".gitkeep",
        REVIEWS_ROOT / "investigations" / ".gitkeep",
        REVIEWS_ROOT / "action_items" / ".gitkeep",
        REVIEWS_ROOT / "templates" / "gate_review.md",
        REVIEWS_ROOT / "templates" / "investigation.md",
        REVIEWS_ROOT / "templates" / "action_item.md",
    ]

    for path in expected_paths:
        assert path.exists(), f"missing customer review template path: {path}"


def test_gate_review_template_keeps_gate_history_metadata() -> None:
    gate_review = (REVIEWS_ROOT / "templates" / "gate_review.md").read_text(encoding="utf-8")

    assert "## Metadata" in gate_review
    assert "gate_run_id:" in gate_review
    assert "gate_history_ref:" in gate_review


def test_customer_template_readme_explains_reviews_and_gate_review() -> None:
    readme = (TEMPLATE_ROOT / "README.md").read_text(encoding="utf-8")

    assert "reviews/" in readme
    assert "Gate Review" in readme
    assert "gate_history" in readme
    assert "gate-decision.json" in readme
    assert "gate-report.json" in readme
    assert "gate-history-summary.json" in readme


def test_reviews_templates_do_not_include_live_secrets_or_endpoints() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in REVIEWS_ROOT.rglob("*") if path.is_file()
    )

    forbidden_patterns = [
        r"https?://",
        r"sk-[A-Za-z0-9_-]+",
        r"ghp_[A-Za-z0-9_]+",
        r"xox[baprs]-[A-Za-z0-9-]+",
        r"Bearer\s+[A-Za-z0-9._-]+",
    ]

    for pattern in forbidden_patterns:
        assert re.search(pattern, combined, flags=re.IGNORECASE) is None


def test_customer_template_quality_pack_keeps_readable_s1_definition_list() -> None:
    quality_pack = (TEMPLATE_ROOT / "quality-pack.yml").read_text(encoding="utf-8")

    assert "- active S1 rows should include a reviewed expected_answer" in quality_pack
    assert "- active S1 rows should include reviewed expected_evidence" in quality_pack
    assert "- active S1 rows should include owner and last_reviewed_at" in quality_pack
    assert "- active S1 rows should include the manual_review_required note marker" in quality_pack
    assert "- active S1 rows should include a failure pattern reference" in quality_pack


def test_customer_template_monthly_gate_uploads_safe_artifact_allowlist() -> None:
    workflow = MONTHLY_GATE_WORKFLOW.read_text(encoding="utf-8")

    assert "--report-mode ci" in workflow
    assert "gate-report-ci.md" in workflow
    assert "gate-report-ci.json" in workflow
    assert "retention-days: 7" in workflow
    assert "logs/customer-poc/gate-report-ci.md" in workflow
    assert "logs/customer-poc/gate-report-ci.json" in workflow
    assert "logs/customer-poc/gate-decision.json" in workflow
    assert "logs/customer-poc/gate-history-summary.json" in workflow

    upload_section = workflow.split("path: |", 1)[1].split("retention-days:", 1)[0]
    upload_lines = [line.strip() for line in upload_section.splitlines() if line.strip()]
    assert "logs/customer-poc/" not in upload_lines
    assert "logs/customer-poc/*" not in upload_lines

    forbidden_uploads = [
        "cases.csv",
        "gate.yml",
        "quality-pack.yml",
        "gate-report.md",
        "gate-report.json",
        ".jsonl",
        "faiss.index",
        "index/meta.json",
    ]
    for forbidden in forbidden_uploads:
        assert forbidden not in upload_section


def test_customer_template_readme_warns_against_customer_data_artifacts() -> None:
    readme = (TEMPLATE_ROOT / "README.md").read_text(encoding="utf-8")

    assert "allowlisted safe metadata" in readme
    assert "Do not upload `logs/customer-poc/`" in readme
    assert "`cases.csv`" in readme
    assert "raw `gate.yml`" in readme
    assert "raw `quality-pack.yml`" in readme
    assert "customer documents" in readme
    assert "raw answers" in readme


def test_customer_template_uses_expected_evidence_metric_name() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in TEMPLATE_ROOT.rglob("*") if path.is_file()
    )

    assert "expected_evidence_hit_rate" in combined
    assert "retrieval_precision" not in combined
    assert "Retrieval precision" not in combined
