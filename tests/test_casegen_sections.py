from __future__ import annotations

import json
import uuid
from pathlib import Path

from rqg.casegen.sections import extract_sections_from_snapshot
from rqg.domain import DocumentSnapshot


def test_extract_sections_from_markdown_headings():
    doc = Path("tests/.tmp") / f"{uuid.uuid4()}-sections.md"
    doc.write_text(
        "# Leave Policy\n\nPaid leave requests must be submitted.\n\n## Approval\n\nManager approval is required.\n",
        encoding="utf-8",
    )
    snapshot = DocumentSnapshot(
        snapshot_id="snapshot-001",
        doc_id="doc-001",
        title="Leave Policy",
        source_path=doc.as_posix(),
        content_hash="hash",
        created_at="2026-03-23T00:00:00Z",
    )

    sections = extract_sections_from_snapshot(snapshot)

    assert len(sections) == 2
    assert sections[0].section_id.endswith("#sec-1")
    assert sections[1].section_id.endswith("#sec-1-1")
    assert sections[1].heading == "Approval"


def test_extract_sections_without_headings_returns_single_section():
    doc = Path("tests/.tmp") / f"{uuid.uuid4()}-plain.md"
    doc.write_text("Paid leave requests must be submitted.", encoding="utf-8")
    snapshot = DocumentSnapshot(
        snapshot_id="snapshot-001",
        doc_id="doc-001",
        title="Plain",
        source_path=doc.as_posix(),
        content_hash="hash",
        created_at="2026-03-23T00:00:00Z",
    )

    sections = extract_sections_from_snapshot(snapshot)

    assert len(sections) == 1
    assert sections[0].content == "Paid leave requests must be submitted."
