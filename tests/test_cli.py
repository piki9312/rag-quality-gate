"""Tests for CLI entry point."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import uuid

import pytest

from rqg.cli import main


class TestCLIHelp:
    def test_main_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "rqg.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "ingest" in result.stdout
        assert "eval" in result.stdout
        assert "check" in result.stdout
        assert "init-snapshot" in result.stdout
        assert "create-sample-case" in result.stdout
        assert "create-sample-gate" in result.stdout

    def test_eval_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "rqg.cli", "eval", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "cases" in result.stdout.lower() or "CASES" in result.stdout


class TestCLIParsing:
    """CLI のパースロジックだけをテスト (実行はモック)。"""

    def test_eval_mock_flag(self):
        """--mock フラグがパーサーに認識されるか。"""
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["eval", "cases.csv", "--mock"])
        assert args.mock is True
        assert args.command == "eval"

    def test_check_defaults(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["check"])
        assert args.command == "check"

    def test_ingest_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["ingest", "docs/"])
        assert args.command == "ingest"
        assert args.docs_dir == "docs/"

    def test_init_snapshot_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "init-snapshot",
                "--snapshot-id",
                "snapshot-001",
                "--doc-id",
                "doc-001",
                "--title",
                "Policy",
                "--source-path",
                "docs/policy.md",
                "--output",
                "snapshot.json",
            ]
        )
        assert args.command == "init-snapshot"
        assert args.output == "snapshot.json"


class TestPhase1CLI:
    def test_create_sample_case_writes_json(self):
        output = Path("tests/.tmp") / f"{uuid.uuid4()}-case.json"

        exit_code = main(["create-sample-case", "--output", str(output)])

        assert exit_code == 0
        assert output.exists()
        assert "sample-case-001" in output.read_text(encoding="utf-8")

    def test_create_sample_gate_writes_json(self):
        output = Path("tests/.tmp") / f"{uuid.uuid4()}-gate.json"

        exit_code = main(["create-sample-gate", "--output", str(output)])

        assert exit_code == 0
        assert output.exists()
        assert '"status": "warn"' in output.read_text(encoding="utf-8")

    def test_init_snapshot_writes_json(self):
        output = Path("tests/.tmp") / f"{uuid.uuid4()}-snapshot.json"

        exit_code = main(
            [
                "init-snapshot",
                "--snapshot-id",
                "snapshot-001",
                "--doc-id",
                "doc-001",
                "--title",
                "Policy",
                "--source-path",
                "docs/policy.md",
                "--content",
                "policy body",
                "--output",
                str(output),
            ]
        )

        assert exit_code == 0
        assert output.exists()
        assert '"doc_id": "doc-001"' in output.read_text(encoding="utf-8")

    def test_ingest_writes_document_snapshot(self):
        docs_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-docs"
        index_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-index"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "policy.md").write_text("# Policy\n\nbody", encoding="utf-8")

        class FakeStore:
            def __init__(self, index_dir):
                self.index_dir = index_dir
                self.index = None

            def add_text(self, source, text):
                return 2

        with patch("rqg.serving.rag.RAGStore", FakeStore):
            exit_code = main(["ingest", str(docs_dir), "--index-dir", str(index_dir)])

        snapshots = list((index_dir / "snapshots").glob("*.json"))
        assert exit_code == 0
        assert len(snapshots) == 1
        content = snapshots[0].read_text(encoding="utf-8")
        assert '"title": "policy"' in content
        assert '"chunk_count": 2' in content
