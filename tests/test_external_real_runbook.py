from __future__ import annotations

from pathlib import Path


RUNBOOK_PATH = Path("docs/demo/external-real-poc-runbook.md")


def test_external_real_runbook_has_required_sections_and_safety_language() -> None:
    text = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "# External Real PoC Runbook" in text
    assert "## 1. 目的" in text
    assert "## 5. 実行手順" in text
    assert "## 8. Go / No-Go 判定基準" in text
    assert "## 10. Security / privacy" in text
    assert "## 12. Non-goals" in text

    assert "**`--mock` を使わないこと。**" in text
    assert "PASS does not guarantee overall production safety" in text
    assert "### NO-GO" in text
    assert "`adapter_config.yml` に secret を書きません" in text
    assert "`execution_mode=external_real` を確認" in text
