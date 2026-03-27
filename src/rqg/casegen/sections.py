"""Document section extraction for case generation."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from rqg.domain import DocumentSnapshot


class DocumentSection(BaseModel):
    """A normalized document section used for candidate generation."""

    section_id: str = Field(..., min_length=1)
    heading: str
    content: str = Field(..., min_length=1)
    level: int = Field(..., ge=1)

    model_config = ConfigDict(extra="forbid")


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def _normalize_document_key(document_key: str) -> str:
    normalized = document_key.strip().replace("\\", "/")
    return normalized or "document"


def _resolve_snapshot_source(snapshot: DocumentSnapshot, snapshot_path: Path | None = None) -> Path:
    candidate = Path(snapshot.source_path)
    if candidate.exists():
        return candidate
    if not candidate.is_absolute() and snapshot_path is not None:
        relative_candidate = (snapshot_path.parent / candidate).resolve()
        if relative_candidate.exists():
            return relative_candidate
    raise FileNotFoundError(f"Document source not found: {snapshot.source_path}")


def _slug_sections(document_key: str, counters: list[int], fallback_index: int) -> str:
    if any(counters):
        active = [str(value) for value in counters if value > 0]
        suffix = "-".join(active)
    else:
        suffix = str(fallback_index)
    return f"{document_key}#sec-{suffix}"


def _build_markdown_sections(document_key: str, text: str) -> list[DocumentSection]:
    lines = text.splitlines()
    sections: list[DocumentSection] = []
    counters = [0] * 6
    current_heading = ""
    current_level = 1
    current_content: list[str] = []
    section_index = 0

    def flush_section() -> None:
        nonlocal section_index, current_content, current_heading, current_level
        content = "\n".join(line for line in current_content).strip()
        if not content:
            return
        section_index += 1
        section_id = _slug_sections(document_key, counters, section_index)
        sections.append(
            DocumentSection(
                section_id=section_id,
                heading=current_heading,
                content=content,
                level=current_level,
            )
        )
        current_content = []

    for raw_line in lines:
        match = _HEADING_RE.match(raw_line)
        if match:
            flush_section()
            current_level = len(match.group(1))
            current_heading = match.group(2).strip()
            counters[current_level - 1] += 1
            for idx in range(current_level, len(counters)):
                counters[idx] = 0
            continue
        current_content.append(raw_line)

    flush_section()
    if sections:
        return sections

    content = text.strip()
    if not content:
        return []
    return [
        DocumentSection(
            section_id=f"{document_key}#sec-1",
            heading="",
            content=content,
            level=1,
        )
    ]


def _build_pdf_sections(document_key: str, source_path: Path) -> list[DocumentSection]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF support requires pypdf to be installed") from exc

    reader = PdfReader(str(source_path))
    sections: list[DocumentSection] = []
    for page_index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        sections.append(
            DocumentSection(
                section_id=f"{document_key}#page-{page_index}",
                heading=f"Page {page_index}",
                content=text,
                level=1,
            )
        )
    return sections


def extract_sections_from_snapshot(
    snapshot: DocumentSnapshot, snapshot_path: str | Path | None = None
) -> list[DocumentSection]:
    """Extract sections from a snapshot's source document."""
    snapshot_file = Path(snapshot_path) if snapshot_path is not None else None
    source_path = _resolve_snapshot_source(snapshot, snapshot_file)
    document_key = _normalize_document_key(snapshot.doc_id or source_path.as_posix())
    suffix = source_path.suffix.lower()
    if suffix in {".md", ".markdown", ".txt"}:
        text = source_path.read_text(encoding="utf-8", errors="ignore")
        return _build_markdown_sections(document_key, text)
    if suffix == ".pdf":
        return _build_pdf_sections(document_key, source_path)
    raise ValueError(f"Unsupported document type for case generation: {suffix}")
