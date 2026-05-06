from __future__ import annotations

from pathlib import Path


def test_customer_facing_sales_docs_exist() -> None:
    for relative_path in [
        "docs/sales/customer_gate_report_template.md",
        "docs/sales/customer_data_handling_onepager.md",
        "docs/sales/post_poc_options_onepager.md",
        "docs/sales/rag_build_scope.md",
        "demos/customer_support_faq_change/before_after_onepager.md",
    ]:
        assert Path(relative_path).exists(), relative_path


def test_readme_links_customer_facing_materials() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "docs/sales/customer_gate_report_template.md" in readme
    assert "docs/sales/customer_data_handling_onepager.md" in readme
    assert "docs/sales/post_poc_options_onepager.md" in readme
    assert "docs/sales/rag_build_scope.md" in readme
