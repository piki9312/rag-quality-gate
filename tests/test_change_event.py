from __future__ import annotations

from pathlib import Path

import pytest

from rqg.cli import build_parser
from rqg.quality.change_event import change_event_to_provenance, load_change_event_file


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_load_change_event_yaml_validates_minimal_schema(tmp_path) -> None:
    path = tmp_path / "change-event.yml"
    path.write_text(
        "\n".join(
            [
                "change_id: change-202605-refund",
                "change_type: document_update",
                "change_summary: Refund policy source update",
                "changed_assets:",
                "  - type: document",
                "    name: refund_policy_v2",
                "    version: v2",
                "    content_hash: example_hash_refund_v2",
                "affected_business_categories:",
                "  - refund",
                "retest_reason: Refund policy changed",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    event = load_change_event_file(path)

    assert event is not None
    assert event.change_id == "change-202605-refund"
    assert event.change_type == "document_update"
    assert event.changed_assets[0].type == "document"
    assert event.changed_assets[0].content_hash == "example_hash_refund_v2"
    assert event.affected_business_categories == ["refund"]
    provenance = change_event_to_provenance(event)
    assert provenance["change_event_id"] == "change-202605-refund"


def test_load_change_event_rejects_invalid_change_type(tmp_path) -> None:
    path = tmp_path / "change-event.yml"
    path.write_text(
        "change_id: change-1\nchange_type: customer_specific_release\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid change-event file"):
        load_change_event_file(path)


def test_change_event_example_template_is_parseable() -> None:
    path = REPO_ROOT / "templates" / "change-event.example.yml"

    event = load_change_event_file(path)

    assert event is not None
    assert event.change_id == "pricing-refund-update-001"
    assert event.change_type == "document_update"
    assert len(event.changed_assets) == 2
    assert event.target_release == ""


def test_change_event_example_template_avoids_secret_like_placeholders() -> None:
    text = (REPO_ROOT / "templates" / "change-event.example.yml").read_text(encoding="utf-8")

    for forbidden in (
        "C:/",
        "C:\\\\",
        "/Users/",
        "/home/",
        "target_release:",
        "path:",
        "api_key",
        "token",
        "password",
        "secret",
        "ACME",
    ):
        assert forbidden not in text


def test_change_event_docs_examples_match_cli_contract() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    runbook = (REPO_ROOT / "docs" / "user-guide" / "poc-monitor-runbook.md").read_text(
        encoding="utf-8"
    )
    poc_guide = (REPO_ROOT / "docs" / "user-guide" / "proof-gate-poc.md").read_text(
        encoding="utf-8"
    )
    combined = "\n".join((readme, runbook, poc_guide))

    assert "rqg gate --change-event change-event.yml" in combined
    assert "rqg check --change-event change-event.yml" in combined
    assert r"\.\.venv" not in combined

    parser = build_parser()
    gate_args = parser.parse_args(
        ["gate", "packs/hr/cases.csv", "--change-event", "change-event.yml"]
    )
    check_args = parser.parse_args(["check", "--change-event", "change-event.yml"])

    assert gate_args.change_event_file == "change-event.yml"
    assert check_args.change_event_file == "change-event.yml"
