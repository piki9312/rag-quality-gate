from __future__ import annotations

import csv
import json
from pathlib import Path

from rqg.cli import main


def _write_snapshot(path: Path, *, snapshot_id: str, doc_id: str, source_path: Path) -> None:
    payload = {
        "snapshot_id": snapshot_id,
        "doc_id": doc_id,
        "title": "Policy",
        "source_path": source_path.as_posix(),
        "content_hash": "hash",
        "created_at": "2026-03-23T00:00:00Z",
        "metadata": {},
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_migrate_cases_json_converts_expected_evidence(tmp_path: Path):
    source_doc = tmp_path / "legacy_policy.md"
    source_doc.write_text("# Policy\n\nlegacy", encoding="utf-8")

    snapshot_file = tmp_path / "snapshot.json"
    _write_snapshot(
        snapshot_file,
        snapshot_id="snap-001",
        doc_id="policy/leave",
        source_path=source_doc,
    )

    cases_file = tmp_path / "cases.json"
    output_file = tmp_path / "migrated_cases.json"
    report_file = tmp_path / "migration_report.json"

    cases_payload = [
        {
            "case_id": "case-001",
            "question": "When should request be submitted?",
            "expected_evidence": [f"{source_doc.as_posix()}#sec-1", "policy/leave#sec-2"],
            "expected_keywords": ["request"],
            "risk_level": "S2",
            "doc_snapshot_id": "snap-001",
        }
    ]
    cases_file.write_text(json.dumps(cases_payload, indent=2), encoding="utf-8")

    exit_code = main(
        [
            "migrate-cases",
            "--cases",
            str(cases_file),
            "--snapshot",
            str(snapshot_file),
            "--output",
            str(output_file),
            "--report",
            str(report_file),
        ]
    )

    assert exit_code == 0

    migrated_payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert migrated_payload[0]["expected_evidence"][0] == "policy/leave#sec-1"
    assert migrated_payload[0]["expected_evidence"][1] == "policy/leave#sec-2"

    summary = json.loads(report_file.read_text(encoding="utf-8"))
    assert summary["converted_case_count"] == 1
    assert summary["converted_evidence_refs"] == 1
    assert summary["unresolved_legacy_refs"] == 0


def test_migrate_cases_csv_converts_expected_evidence(tmp_path: Path):
    source_doc = tmp_path / "legacy_policy.md"
    source_doc.write_text("# Policy\n\nlegacy", encoding="utf-8")

    snapshot_file = tmp_path / "snapshot.json"
    _write_snapshot(
        snapshot_file,
        snapshot_id="snap-001",
        doc_id="policy/leave",
        source_path=source_doc,
    )

    cases_file = tmp_path / "cases.csv"
    output_file = tmp_path / "migrated_cases.csv"

    with open(cases_file, "w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=[
                "case_id",
                "question",
                "expected_evidence",
                "expected_keywords",
                "risk_level",
                "doc_snapshot_id",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "case-001",
                "question": "When should request be submitted?",
                "expected_evidence": f"{source_doc.as_posix()}#sec-1;other/path#sec-2",
                "expected_keywords": "request",
                "risk_level": "S2",
                "doc_snapshot_id": "snap-001",
                "notes": "",
            }
        )

    exit_code = main(
        [
            "migrate-cases",
            "--cases",
            str(cases_file),
            "--snapshot",
            str(snapshot_file),
            "--output",
            str(output_file),
        ]
    )

    assert exit_code == 0

    with open(output_file, "r", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        rows = list(reader)

    assert rows[0]["expected_evidence"] == "policy/leave#sec-1;other/path#sec-2"


def test_migrate_cases_requires_snapshot_input(tmp_path: Path, capsys):
    cases_file = tmp_path / "cases.json"
    output_file = tmp_path / "migrated_cases.json"
    cases_file.write_text("[]", encoding="utf-8")

    exit_code = main(
        [
            "migrate-cases",
            "--cases",
            str(cases_file),
            "--output",
            str(output_file),
        ]
    )

    stderr = capsys.readouterr().err
    assert exit_code == 1
    assert "Provide --snapshot and/or --snapshot-dir" in stderr
