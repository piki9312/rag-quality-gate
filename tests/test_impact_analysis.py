from __future__ import annotations

import json
from pathlib import Path
import uuid

from rqg.cli import main
from rqg.domain import DocumentSnapshot, EvalCase
from rqg.quality.impact_analysis import build_impact_report, detect_changed_evidence_ids


def _make_snapshot(path: Path, *, snapshot_id: str) -> DocumentSnapshot:
    text = path.read_text(encoding="utf-8")
    return DocumentSnapshot(
        snapshot_id=snapshot_id,
        doc_id=path.as_posix(),
        title=path.stem,
        source_path=path.as_posix(),
        content_hash=str(hash(text)),
        created_at="2026-03-23T00:00:00Z",
        metadata={},
    )


def test_changed_evidence_ids_and_impacted_cases_detected():
    old_doc = Path("tests/.tmp") / f"{uuid.uuid4()}-policy-old.md"
    new_doc = Path("tests/.tmp") / f"{uuid.uuid4()}-policy-new.md"
    old_doc.write_text("# Policy\n\nSubmit request 5 business days in advance.", encoding="utf-8")
    new_doc.write_text("# Policy\n\nSubmit request 3 business days in advance.", encoding="utf-8")

    old_snapshot = _make_snapshot(old_doc, snapshot_id="snap-old")
    new_snapshot = _make_snapshot(new_doc, snapshot_id="snap-new")

    old_section_id = f"{old_doc.as_posix()}#sec-1"
    case = EvalCase(
        case_id="case-001",
        question="When should request be submitted?",
        expected_evidence=[old_section_id],
        expected_keywords=["request"],
        risk_level="S2",
        doc_snapshot_id="snap-old",
    )

    changed = detect_changed_evidence_ids(old_snapshot, new_snapshot)
    report = build_impact_report(old_snapshot, new_snapshot, [case])

    assert old_section_id in changed
    assert "case-001" in report.impacted_case_ids
    assert any(detail["matched_evidence_id"] == old_section_id for detail in report.details)


def test_impact_report_json_serializable():
    doc = Path("tests/.tmp") / f"{uuid.uuid4()}-policy.md"
    doc.write_text("# Policy\n\nKeep records for one year.", encoding="utf-8")

    snapshot = _make_snapshot(doc, snapshot_id="snap-001")
    case = EvalCase(
        case_id="case-001",
        question="How long should records be kept?",
        expected_evidence=[f"{doc.as_posix()}#sec-1"],
        expected_keywords=["records"],
        risk_level="S2",
        doc_snapshot_id="snap-001",
    )

    report = build_impact_report(snapshot, snapshot, [case])
    payload = report.model_dump_json()

    assert '"old_snapshot_id":"snap-001"' in payload
    assert '"changed_evidence_ids":[]' in payload
    assert '"impacted_case_ids":[]' in payload


def test_empty_cases_file_does_not_crash_and_outputs_empty_impacted(tmp_path: Path):
    old_doc = tmp_path / "old.md"
    new_doc = tmp_path / "new.md"
    old_snapshot_file = tmp_path / "old_snapshot.json"
    new_snapshot_file = tmp_path / "new_snapshot.json"
    cases_file = tmp_path / "cases.json"
    output_file = tmp_path / "impact_report.json"

    old_doc.write_text("# A\n\nOne", encoding="utf-8")
    new_doc.write_text("# A\n\nTwo", encoding="utf-8")
    old_snapshot = _make_snapshot(old_doc, snapshot_id="old")
    new_snapshot = _make_snapshot(new_doc, snapshot_id="new")

    old_snapshot_file.write_text(old_snapshot.model_dump_json(indent=2), encoding="utf-8")
    new_snapshot_file.write_text(new_snapshot.model_dump_json(indent=2), encoding="utf-8")
    cases_file.write_text("[]", encoding="utf-8")

    exit_code = main(
        [
            "impact",
            "--old-snapshot",
            str(old_snapshot_file),
            "--new-snapshot",
            str(new_snapshot_file),
            "--cases",
            str(cases_file),
            "--output",
            str(output_file),
        ]
    )

    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["impacted_case_ids"] == []


def test_changed_evidence_empty_yields_no_impacted_cases():
    doc = Path("tests/.tmp") / f"{uuid.uuid4()}-same.md"
    doc.write_text("# Same\n\nNo change.", encoding="utf-8")
    snapshot_old = _make_snapshot(doc, snapshot_id="old")
    snapshot_new = _make_snapshot(doc, snapshot_id="new")

    case = EvalCase(
        case_id="case-001",
        question="No change question",
        expected_evidence=[f"{doc.as_posix()}#sec-1"],
        expected_keywords=[],
        risk_level="S2",
        doc_snapshot_id="old",
    )

    report = build_impact_report(snapshot_old, snapshot_new, [case])
    assert report.changed_evidence_ids == []
    assert report.impacted_case_ids == []


def test_invalid_snapshot_input_fails_with_readable_error(tmp_path: Path, capsys):
    invalid_old = tmp_path / "invalid_old.json"
    valid_new_doc = tmp_path / "new.md"
    valid_new_snapshot = tmp_path / "new_snapshot.json"
    cases_file = tmp_path / "cases.json"
    output_file = tmp_path / "impact_report.json"

    invalid_old.write_text('{"snapshot_id":"old"}', encoding="utf-8")
    valid_new_doc.write_text("# Policy\n\nBody", encoding="utf-8")
    new_snapshot = _make_snapshot(valid_new_doc, snapshot_id="new")
    valid_new_snapshot.write_text(new_snapshot.model_dump_json(indent=2), encoding="utf-8")
    cases_file.write_text("[]", encoding="utf-8")

    exit_code = main(
        [
            "impact",
            "--old-snapshot",
            str(invalid_old),
            "--new-snapshot",
            str(valid_new_snapshot),
            "--cases",
            str(cases_file),
            "--output",
            str(output_file),
        ]
    )

    stderr = capsys.readouterr().err
    assert exit_code == 1
    assert "Failed to load old snapshot" in stderr
