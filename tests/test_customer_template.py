from __future__ import annotations

import re
from pathlib import Path

TEMPLATE_ROOT = Path("templates/customer-rqg-template")
REVIEWS_ROOT = TEMPLATE_ROOT / "reviews"


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
