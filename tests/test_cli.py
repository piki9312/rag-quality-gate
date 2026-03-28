"""Tests for CLI entry point."""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        assert "gen-cases" in result.stdout
        assert "impact" in result.stdout
        assert "migrate-cases" in result.stdout

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

    def test_gen_cases_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "gen-cases",
                "--snapshot",
                "snapshot.json",
                "--output",
                "cases.json",
                "--review-output",
                "cases.md",
                "--mode",
                "hybrid",
                "--max-cases",
                "10",
                "--use-llm",
            ]
        )
        assert args.command == "gen-cases"
        assert args.mode == "hybrid"
        assert args.use_llm is True

    def test_migrate_cases_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "migrate-cases",
                "--cases",
                "cases.json",
                "--snapshot",
                "snapshots/old.json",
                "--snapshot-dir",
                "snapshots",
                "--output",
                "migrated.json",
                "--report",
                "migration_report.json",
            ]
        )
        assert args.command == "migrate-cases"
        assert args.snapshot == ["snapshots/old.json"]
        assert args.snapshot_dir == "snapshots"
        assert args.report == "migration_report.json"

    def test_impact_args_with_simulation_options(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "impact",
                "--old-snapshot",
                "old.json",
                "--new-snapshot",
                "new.json",
                "--cases",
                "cases.json",
                "--output",
                "impact.json",
                "--reference-date",
                "2026-07-01",
                "--strict-only",
            ]
        )
        assert args.command == "impact"
        assert args.reference_date == "2026-07-01"
        assert args.strict_only is True


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

    def test_gen_cases_writes_json_and_markdown(self):
        source_doc = Path("tests/.tmp") / f"{uuid.uuid4()}-rules.md"
        snapshot_file = Path("tests/.tmp") / f"{uuid.uuid4()}-snapshot.json"
        output_file = Path("tests/.tmp") / f"{uuid.uuid4()}-cases.json"
        review_file = Path("tests/.tmp") / f"{uuid.uuid4()}-cases.md"

        source_doc.write_text(
            "# Leave Policy\n\nPaid leave requests must be submitted 5 business days in advance.\n",
            encoding="utf-8",
        )
        snapshot = {
            "snapshot_id": "snapshot-001",
            "doc_id": "doc-001",
            "title": "Leave Policy",
            "source_path": source_doc.as_posix(),
            "content_hash": "abc123",
            "created_at": "2026-03-23T00:00:00Z",
            "version": None,
            "metadata": {},
        }
        import json

        snapshot_file.write_text(json.dumps(snapshot), encoding="utf-8")

        exit_code = main(
            [
                "gen-cases",
                "--snapshot",
                str(snapshot_file),
                "--output",
                str(output_file),
                "--review-output",
                str(review_file),
            ]
        )

        assert exit_code == 0
        assert output_file.exists()
        assert review_file.exists()
        assert "leave_policy_001" in output_file.read_text(encoding="utf-8")
        review_content = review_file.read_text(encoding="utf-8")
        assert "# Eval Case Review" in review_content
        assert "## Case: leave_policy_001" in review_content

    def test_gen_cases_without_review_output_writes_only_json(self):
        source_doc = Path("tests/.tmp") / f"{uuid.uuid4()}-rules-no-review.md"
        snapshot_file = Path("tests/.tmp") / f"{uuid.uuid4()}-snapshot-no-review.json"
        output_file = Path("tests/.tmp") / f"{uuid.uuid4()}-cases-no-review.json"
        review_file = Path("tests/.tmp") / f"{uuid.uuid4()}-cases-no-review.md"

        source_doc.write_text(
            "# Leave Policy\n\nPaid leave requests must be submitted 5 business days in advance.\n",
            encoding="utf-8",
        )
        snapshot = {
            "snapshot_id": "snapshot-001",
            "doc_id": "doc-001",
            "title": "Leave Policy",
            "source_path": source_doc.as_posix(),
            "content_hash": "abc123",
            "created_at": "2026-03-23T00:00:00Z",
            "version": None,
            "metadata": {},
        }
        import json

        snapshot_file.write_text(json.dumps(snapshot), encoding="utf-8")

        exit_code = main(
            [
                "gen-cases",
                "--snapshot",
                str(snapshot_file),
                "--output",
                str(output_file),
            ]
        )

        assert exit_code == 0
        assert output_file.exists()
        assert not review_file.exists()
