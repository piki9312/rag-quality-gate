"""CSV preview and writer helpers for pattern draft review artifacts.

These helpers emit formal-schema rows because the existing merge-cases flow can
consume them as review CSV input. The output is still a review artifact, not a
source-of-truth cases.csv.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Mapping, Sequence

from rqg.quality.case_schema import FORMAL_CASE_FIELDS, VALID_SEVERITIES

_REQUIRED_NOTE_MARKERS = (
    "generated_by:case_draft_engine",
    "case_type:generated-draft",
    "answer_status:unapproved-draft",
)


def draft_case_rows_to_csv_text(rows: Sequence[Mapping[str, str]]) -> str:
    """Return formal-schema review CSV text for needs_review draft rows."""
    normalized_rows = validate_draft_case_rows(rows)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FORMAL_CASE_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(normalized_rows)
    return buffer.getvalue()


def write_draft_case_rows_csv(rows: Sequence[Mapping[str, str]], path: Path) -> None:
    """Write needs_review draft rows as a review CSV artifact."""
    csv_text = draft_case_rows_to_csv_text(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(csv_text, encoding="utf-8", newline="")


def validate_draft_case_rows(rows: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Validate and normalize multiple draft case rows."""
    return [validate_draft_case_row(row) for row in rows]


def validate_draft_case_row(row: Mapping[str, str]) -> dict[str, str]:
    """Validate and normalize one draft case row.

    Unknown fields are ignored at this boundary. Missing formal fields are
    represented as empty strings after safety validation.
    """
    normalized = {field: str(row.get(field, "") or "") for field in FORMAL_CASE_FIELDS}
    status = normalized["status"].strip()
    if status == "active":
        raise ValueError("Draft CSV writer refuses active rows")
    if status != "needs_review":
        raise ValueError("Draft CSV writer only accepts status=needs_review rows")
    severity = normalized["severity"].strip().upper()
    if not severity:
        raise ValueError("Draft CSV writer requires severity")
    if severity not in VALID_SEVERITIES:
        allowed = ", ".join(sorted(VALID_SEVERITIES))
        raise ValueError(
            f"Draft CSV writer only accepts severity values {allowed}; got {normalized['severity']!r}"
        )
    normalized["severity"] = severity
    if not normalized["question"].strip():
        raise ValueError("Draft CSV writer requires non-empty question")
    if not normalized["expected_answer"].strip():
        raise ValueError("Draft CSV writer requires non-empty expected_answer")
    notes = normalized["notes"]
    for marker in _REQUIRED_NOTE_MARKERS:
        if marker not in notes:
            raise ValueError(f"Draft CSV writer row missing notes marker: {marker}")
    return normalized
