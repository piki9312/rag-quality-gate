"""Tests for CLI entry point."""

from __future__ import annotations

import csv
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
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
        assert "gate" in result.stdout
        assert "check" in result.stdout
        assert "init-snapshot" in result.stdout
        assert "create-sample-case" in result.stdout
        assert "create-sample-gate" in result.stdout
        assert "init-pack" in result.stdout
        assert "gen-cases" in result.stdout
        assert "impact" in result.stdout
        assert "migrate-cases" in result.stdout
        assert "merge-cases" in result.stdout
        assert "validate-cases" in result.stdout

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
        assert args.reset_log_dir is False

    def test_eval_reset_log_dir_flag(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["eval", "cases.csv", "--reset-log-dir"])
        assert args.command == "eval"
        assert args.reset_log_dir is True

    def test_check_defaults(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["check"])
        assert args.command == "check"
        assert args.quality_pack is None
        assert args.max_overall_drop_pct is None
        assert args.max_s1_drop_pct is None

    def test_gate_defaults(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["gate", "packs/hr/cases.csv"])
        assert args.command == "gate"
        assert args.cases == "packs/hr/cases.csv"
        assert args.log_dir == "runs/quality"
        assert args.cases_file is None
        assert args.max_overall_drop_pct is None
        assert args.max_s1_drop_pct is None
        assert args.reset_log_dir is False

    def test_check_quality_pack_arg(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["check", "--quality-pack", "packs/hr/quality-pack.yml"])
        assert args.command == "check"
        assert args.quality_pack == "packs/hr/quality-pack.yml"

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

    def test_impact_args(self):
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
            ]
        )
        assert args.command == "impact"
        assert args.old_snapshot == "old.json"
        assert args.new_snapshot == "new.json"

    def test_merge_cases_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "merge-cases",
                "--cases",
                "packs/hr/cases.csv",
                "--review",
                "runs/review.csv",
                "--output",
                "packs/hr/cases.merged.csv",
                "--report",
                "runs/merge_report.json",
            ]
        )
        assert args.command == "merge-cases"
        assert args.cases == "packs/hr/cases.csv"
        assert args.review == "runs/review.csv"
        assert args.output == "packs/hr/cases.merged.csv"
        assert args.in_place is False
        assert args.dry_run is False
        assert args.report == "runs/merge_report.json"

    def test_init_pack_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["init-pack", "packs/my_pack", "--force"])
        assert args.command == "init-pack"
        assert args.output_dir == "packs/my_pack"
        assert args.profile == "demo_cycle"
        assert args.force is True

    def test_init_pack_profile_alias_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["init-pack", "packs/sample_pack", "--profile", "sample"])
        assert args.command == "init-pack"
        assert args.output_dir == "packs/sample_pack"
        assert args.profile == "sample"

    def test_init_pack_profile_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["init-pack", "packs/wiki_pack", "--profile", "wiki"])
        assert args.command == "init-pack"
        assert args.output_dir == "packs/wiki_pack"
        assert args.profile == "wiki"

    def test_init_pack_list_profiles_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["init-pack", "--list-profiles"])
        assert args.command == "init-pack"
        assert args.output_dir is None
        assert args.list_profiles is True


class TestPhase1CLI:
    def test_ingest_rejects_index_dir_under_runs(self, capsys):
        docs_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "doc.md").write_text("# test", encoding="utf-8")

        exit_code = main(["ingest", str(docs_dir), "--index-dir", "runs/test-index"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "must be outside runs/" in captured.err

    def test_eval_rejects_index_dir_under_runs_before_loading_cases(self, capsys):
        with patch("rqg.quality.loader.load_cases") as load_cases_mock:
            exit_code = main(
                [
                    "eval",
                    "packs/hr/cases.csv",
                    "--index-dir",
                    "runs/test-index",
                    "--mock",
                ]
            )

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "must be outside runs/" in captured.err
        load_cases_mock.assert_not_called()

    def test_gate_rejects_index_dir_under_runs_before_eval_and_check(self, capsys):
        with patch("rqg.cli.cmd_eval") as eval_mock:
            with patch("rqg.cli.cmd_check") as check_mock:
                exit_code = main(
                    [
                        "gate",
                        "packs/hr/cases.csv",
                        "--index-dir",
                        "runs/test-index",
                        "--mock",
                    ]
                )

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "must be outside runs/" in captured.err
        eval_mock.assert_not_called()
        check_mock.assert_not_called()

    def test_gate_runs_check_even_if_eval_has_failures(self):
        with patch("rqg.cli.cmd_eval", return_value=1) as eval_mock:
            with patch("rqg.cli.cmd_check", return_value=0) as check_mock:
                exit_code = main(["gate", "packs/hr/cases.csv", "--mock"])

        assert exit_code == 0
        eval_mock.assert_called_once()
        check_mock.assert_called_once()
        check_args = check_mock.call_args.args[0]
        assert check_args.log_dir == "runs/quality"
        assert check_args.cases_file == "packs/hr/cases.csv"

    def test_gate_allows_cases_file_override(self):
        with patch("rqg.cli.cmd_eval", return_value=0):
            with patch("rqg.cli.cmd_check", return_value=1) as check_mock:
                exit_code = main(
                    [
                        "gate",
                        "packs/hr/cases.csv",
                        "--cases-file",
                        "packs/wiki/cases.csv",
                    ]
                )

        assert exit_code == 1
        check_args = check_mock.call_args.args[0]
        assert check_args.cases_file == "packs/wiki/cases.csv"

    def test_gate_passes_reset_log_dir_to_eval(self):
        with patch("rqg.cli.cmd_eval", return_value=0) as eval_mock:
            with patch("rqg.cli.cmd_check", return_value=0):
                exit_code = main(["gate", "packs/hr/cases.csv", "--reset-log-dir"])

        assert exit_code == 0
        eval_args = eval_mock.call_args.args[0]
        assert eval_args.reset_log_dir is True

    def test_eval_with_reset_log_dir_cleans_previous_artifacts(self):
        log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-reset-logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "20260101.jsonl").write_text("{}\n", encoding="utf-8")
        (log_dir / "gate-report.md").write_text("old", encoding="utf-8")
        (log_dir / "gate-decision.json").write_text("{}", encoding="utf-8")
        (log_dir / "gate-decisions.jsonl").write_text("{}\n", encoding="utf-8")
        (log_dir / "keep.txt").write_text("keep", encoding="utf-8")

        fake_run = SimpleNamespace(
            run_id="run-reset",
            total=0,
            passed=0,
            failed=0,
            pass_rate=100.0,
            results=[],
        )

        with patch("rqg.quality.loader.load_cases", return_value=[]):
            with patch("rqg.serving.rag.RAGStore") as store_cls:
                store_cls.return_value.index = object()
                with patch("rqg.quality.runner.RAGQualityRunner") as runner_cls:
                    runner_cls.return_value.run_all.return_value = fake_run
                    runner_cls.save_jsonl.return_value = log_dir / "20260407.jsonl"

                    exit_code = main(
                        [
                            "eval",
                            "packs/hr/cases.csv",
                            "--log-dir",
                            str(log_dir),
                            "--reset-log-dir",
                            "--mock",
                        ]
                    )

        assert exit_code == 0
        assert not (log_dir / "20260101.jsonl").exists()
        assert not (log_dir / "gate-report.md").exists()
        assert not (log_dir / "gate-decision.json").exists()
        assert not (log_dir / "gate-decisions.jsonl").exists()
        assert (log_dir / "keep.txt").exists()

    def test_init_pack_list_profiles(self, capsys):
        exit_code = main(["init-pack", "--list-profiles"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "Available init-pack profiles" in captured.out
        assert "demo_cycle" in captured.out
        assert "sample" in captured.out
        assert "sample -> demo_cycle" in captured.out
        assert "hr" in captured.out
        assert "wiki" in captured.out

    def test_init_pack_requires_output_dir_without_list(self, capsys):
        exit_code = main(["init-pack"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "output_dir is required" in captured.err

    def test_init_pack_scaffolds_template(self):
        target = Path("tests/.tmp") / f"{uuid.uuid4()}-pack"

        exit_code = main(["init-pack", str(target)])

        assert exit_code == 0
        assert (target / "cases.csv").exists()
        assert (target / "gate.yml").exists()
        assert (target / "quality-pack.yml").exists()
        assert (target / "documents" / "leave_policy.md").exists()

    def test_init_pack_scaffolds_sample_alias(self):
        target = Path("tests/.tmp") / f"{uuid.uuid4()}-pack-sample-alias"

        exit_code = main(["init-pack", str(target), "--profile", "sample"])

        assert exit_code == 0
        assert (target / "cases.csv").exists()
        assert (target / "gate.yml").exists()
        assert (target / "quality-pack.yml").exists()
        assert (target / "documents" / "leave_policy.md").exists()

    def test_init_pack_scaffolds_wiki_profile(self):
        target = Path("tests/.tmp") / f"{uuid.uuid4()}-pack-wiki"

        exit_code = main(["init-pack", str(target), "--profile", "wiki"])

        assert exit_code == 0
        assert (target / "cases.csv").exists()
        assert (target / "gate.yml").exists()
        assert (target / "quality-pack.yml").exists()
        assert (target / "documents" / "access_faq.md").exists()
        assert (target / "documents" / "security_runbook.md").exists()

    def test_init_pack_fails_on_non_empty_target_without_force(self):
        target = Path("tests/.tmp") / f"{uuid.uuid4()}-pack-non-empty"
        target.mkdir(parents=True, exist_ok=True)
        (target / "existing.txt").write_text("already here", encoding="utf-8")

        exit_code = main(["init-pack", str(target)])

        assert exit_code == 1
        assert (target / "existing.txt").exists()

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

    def test_gen_cases_writes_ops_ready_review_csv(self):
        source_doc = Path("tests/.tmp") / f"{uuid.uuid4()}-rules-review-csv.md"
        snapshot_file = Path("tests/.tmp") / f"{uuid.uuid4()}-snapshot-review-csv.json"
        output_file = Path("tests/.tmp") / f"{uuid.uuid4()}-cases-review-csv.json"
        review_file = Path("tests/.tmp") / f"{uuid.uuid4()}-cases-review.csv"

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

        with open(review_file, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        assert len(rows) == 1
        row = rows[0]
        assert row["severity"] == "S2"
        assert row["expected_evidence"].endswith("#sec-1")

    def test_merge_cases_writes_merged_csv_and_report(self):
        base_file = Path("tests/.tmp") / f"{uuid.uuid4()}-cases-base.csv"
        review_file = Path("tests/.tmp") / f"{uuid.uuid4()}-cases-review.csv"
        output_file = Path("tests/.tmp") / f"{uuid.uuid4()}-cases-merged.csv"
        report_file = Path("tests/.tmp") / f"{uuid.uuid4()}-merge-report.json"

        base_rows = [
            {
                "case_id": "leave_001",
                "name": "leave baseline",
                "severity": "S1",
                "question": "old question",
                "expected_evidence": "docs/hr.md#sec-1",
                "expected_keywords": "old",
                "expected_answer": "base answer",
                "category": "policy",
                "owner": "hr-team",
                "min_case_score": "100",
                "last_reviewed_at": "2026-04-01",
            }
        ]
        with open(base_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=base_rows[0].keys())
            writer.writeheader()
            writer.writerows(base_rows)

        review_rows = [
            {
                "case_id": "leave_001",
                "name": "generated leave",
                "severity": "S2",
                "question": "new question",
                "expected_evidence": "docs/hr.md#sec-2",
                "expected_keywords": "new;keyword",
                "expected_answer": "generated answer",
                "category": "generated",
                "owner": "qa-team",
                "min_case_score": "85",
                "last_reviewed_at": "2026-04-05",
            },
            {
                "case_id": "leave_002",
                "question": "added question",
                "expected_evidence": "docs/hr.md#sec-3",
                "risk_level": "S2",
            },
        ]
        with open(review_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "case_id",
                    "name",
                    "severity",
                    "question",
                    "expected_evidence",
                    "expected_keywords",
                    "expected_answer",
                    "category",
                    "owner",
                    "min_case_score",
                    "last_reviewed_at",
                    "risk_level",
                ],
            )
            writer.writeheader()
            writer.writerows(review_rows)

        exit_code = main(
            [
                "merge-cases",
                "--cases",
                str(base_file),
                "--review",
                str(review_file),
                "--output",
                str(output_file),
                "--report",
                str(report_file),
            ]
        )

        assert exit_code == 0
        assert output_file.exists()
        assert report_file.exists()

        with open(output_file, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

        by_id = {row["case_id"]: row for row in rows}
        assert len(rows) == 2
        assert by_id["leave_001"]["question"] == "new question"
        assert by_id["leave_001"]["expected_evidence"] == "docs/hr.md#sec-2"
        assert by_id["leave_001"]["owner"] == "hr-team"
        assert by_id["leave_001"]["category"] == "policy"
        assert by_id["leave_002"]["question"] == "added question"
        assert by_id["leave_002"]["expected_evidence"] == "docs/hr.md#sec-3"
        assert by_id["leave_002"]["severity"] == "S2"

        import json

        report = json.loads(report_file.read_text(encoding="utf-8"))
        assert report["base_cases"] == 1
        assert report["review_cases"] == 2
        assert report["merged_cases"] == 2
        assert report["updated_case_ids"] == ["leave_001"]
        assert report["added_case_ids"] == ["leave_002"]
        assert report["matched_by_content_review_case_ids"] == []


class TestValidateCasesCLI:
    """validate-cases サブコマンドのテスト。"""

    def _write_csv(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def test_validate_cases_parse_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["validate-cases", "--cases", "packs/hr/cases.csv"])
        assert args.command == "validate-cases"
        assert args.cases == "packs/hr/cases.csv"

    def test_validate_cases_valid_csv_returns_0(self):
        csv_path = Path("tests/.tmp") / f"{uuid.uuid4()}-valid.csv"
        self._write_csv(
            csv_path,
            [
                {
                    "case_id": "c001",
                    "question": "What is X?",
                    "expected_answer": "X is Y.",
                    "status": "active",
                    "severity": "S1",
                }
            ],
        )
        assert main(["validate-cases", "--cases", str(csv_path)]) == 0

    def test_validate_cases_invalid_csv_returns_1(self):
        csv_path = Path("tests/.tmp") / f"{uuid.uuid4()}-invalid.csv"
        self._write_csv(
            csv_path,
            [
                {
                    "case_id": "",
                    "question": "",
                    "expected_answer": "",
                    "status": "active",
                }
            ],
        )
        assert main(["validate-cases", "--cases", str(csv_path)]) == 1

    def test_validate_cases_warn_only_returns_0(self):
        csv_path = Path("tests/.tmp") / f"{uuid.uuid4()}-warn.csv"
        self._write_csv(
            csv_path,
            [
                {
                    "case_id": "c001",
                    "question": "What is X?",
                    "expected_answer": "",
                    "status": "draft",
                }
            ],
        )
        assert main(["validate-cases", "--cases", str(csv_path)]) == 0

    def test_validate_cases_missing_file_returns_1(self):
        assert main(["validate-cases", "--cases", "nonexistent.csv"]) == 1


class TestMergeCasesValidation:
    """merge-cases --validate / --no-validate のテスト。"""

    def _write_csv(self, path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fnames = fieldnames or list(rows[0].keys())
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_merge_cases_validate_default_on(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["merge-cases", "--cases", "a.csv", "--review", "b.csv", "--output", "c.csv"]
        )
        assert args.validate is True

    def test_merge_cases_no_validate_flag(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["merge-cases", "--cases", "a.csv", "--review", "b.csv", "--output", "c.csv", "--no-validate"]
        )
        assert args.validate is False

    def test_merge_cases_validation_blocks_invalid(self):
        base_path = Path("tests/.tmp") / f"{uuid.uuid4()}-base.csv"
        review_path = Path("tests/.tmp") / f"{uuid.uuid4()}-review.csv"
        output_path = Path("tests/.tmp") / f"{uuid.uuid4()}-out.csv"

        self._write_csv(
            base_path,
            [{"case_id": "c001", "question": "Q?", "expected_answer": "A", "status": "active"}],
        )
        # Review adds a row that merges OK but fails validation (empty question + bad status)
        self._write_csv(
            review_path,
            [{"case_id": "c_bad", "question": "", "expected_answer": "", "status": "INVALID_STATUS"}],
        )

        rc = main(
            ["merge-cases", "--cases", str(base_path), "--review", str(review_path), "--output", str(output_path)]
        )
        assert rc == 1
        assert not output_path.exists()

    def test_merge_cases_no_validate_allows_invalid(self):
        base_path = Path("tests/.tmp") / f"{uuid.uuid4()}-base.csv"
        review_path = Path("tests/.tmp") / f"{uuid.uuid4()}-review.csv"
        output_path = Path("tests/.tmp") / f"{uuid.uuid4()}-out.csv"

        self._write_csv(
            base_path,
            [{"case_id": "c001", "question": "Q?", "expected_answer": "A", "status": "active"}],
        )
        self._write_csv(
            review_path,
            [{"case_id": "c_bad", "question": "", "expected_answer": "", "status": "INVALID_STATUS"}],
        )

        rc = main(
            [
                "merge-cases",
                "--cases", str(base_path),
                "--review", str(review_path),
                "--output", str(output_path),
                "--no-validate",
            ]
        )
        assert rc == 0
        assert output_path.exists()
