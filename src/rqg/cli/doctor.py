"""rqg doctor sub-command for lightweight environment diagnostics."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import os
import platform
import sys


OPTIONAL_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    ("httpx", "httpx"),
    ("faiss", "faiss"),
    ("sentence_transformers", "sentence_transformers"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
)


def _rqg_version() -> str:
    try:
        return importlib.metadata.version("rag-quality-gate")
    except importlib.metadata.PackageNotFoundError:
        try:
            from rqg import __version__

            return __version__
        except Exception:
            return "unknown"


def _is_installed(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def build_doctor_report() -> str:
    """Build a stable, human-readable environment report."""
    lines = [
        "RQG Doctor",
        "",
        "Environment:",
        f"- Python: {sys.version.split()[0]}",
        f"- Platform: {platform.platform()}",
        f"- RQG version: {_rqg_version()}",
        f"- EMB_MODEL: {os.getenv('EMB_MODEL') or '(not set)'}",
        "",
        "Optional dependencies:",
    ]

    for label, module_name in OPTIONAL_DEPENDENCIES:
        status = "installed" if _is_installed(module_name) else "not installed"
        lines.append(f"- {label}: {status}")

    lines.extend(
        [
            "",
            "Recommended installs:",
            "- base: pip install -e .",
            '- external: pip install -e ".[external]"',
            '- embedding: pip install -e ".[embedding]"',
            '- dev: pip install -e ".[dev]"',
            '- all: pip install -e ".[all]"',
            "",
            "Notes:",
            "- Use base for validate-pack, checking existing logs, and report viewing.",
            "- Use external for HTTP RAG adapter diagnostics without local FAISS.",
            "- Use embedding for local document gate demos that build a FAISS index.",
            "- Use all for full local test runs and CI-equivalent validation.",
            "- For deterministic client demos, set EMB_MODEL=local-fallback-hash-embedding.",
        ]
    )

    if platform.system() == "Windows":
        lines.extend(
            [
                "",
                "Windows PowerShell UTF-8 setup:",
                "chcp 65001",
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8",
                "$OutputEncoding = [System.Text.Encoding]::UTF8",
            ]
        )

    return "\n".join(lines) + "\n"


def cmd_doctor(args: argparse.Namespace) -> int:
    """Print environment diagnostics for first-time users."""
    print(build_doctor_report(), end="")
    return 0
