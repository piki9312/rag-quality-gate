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
from rqg.quality.models import QATestCase


def _subparser_option_strings(command: str) -> set[str]:
    from rqg.cli import build_parser

    parser = build_parser()
    subparsers_action = next(
        action
        for action in parser._actions
        if getattr(action, "choices", None) and command in action.choices
    )
    subparser = subparsers_action.choices[command]
    return {
        option
        for action in subparser._actions
        for option in action.option_strings
    }


def _create_pack_dir(
    base_dir: Path,
    *,
    include_cases: bool = True,
    include_docs: bool = True,
    include_quality_pack: bool = True,
    include_gate_config: bool = True,
) -> Path:
    pack_dir = base_dir / f"pack-{uuid.uuid4().hex[:8]}"
    pack_dir.mkdir(parents=True, exist_ok=True)

    if include_cases:
        (pack_dir / "cases.csv").write_text("case_id,name\n", encoding="utf-8")
    if include_docs:
        docs_dir = pack_dir / "documents"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "doc.md").write_text("# doc\n", encoding="utf-8")
    if include_quality_pack:
        (pack_dir / "quality-pack.yml").write_text("pack:\n  review_steward: qa\n", encoding="utf-8")
    if include_gate_config:
        (pack_dir / "gate.yml").write_text("s1_pass_rate: 100\n", encoding="utf-8")

    return pack_dir


class TestCLIHelp:
    def test_main_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "rqg.cli", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "ingest" in result.stdout
        assert "doctor" in result.stdout
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
        assert "validate-pack" in result.stdout
        assert "history" in result.stdout
        assert "monthly-summary" in result.stdout
        assert "export-weekly-review" in result.stdout
        assert "validate-connection" in result.stdout
        assert "serve-http-rag" in result.stdout
        assert "serve-dashboard" in result.stdout

    def test_doctor_command_succeeds(self):
        result = subprocess.run(
            [sys.executable, "-m", "rqg.cli", "doctor"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "RQG Doctor" in result.stdout
        assert "Python:" in result.stdout
        assert "Platform:" in result.stdout
        assert "RQG version:" in result.stdout
        assert "EMB_MODEL:" in result.stdout
        assert "Optional dependencies:" in result.stdout
        assert "httpx:" in result.stdout
        assert "sentence_transformers:" in result.stdout
        assert "Recommended installs" in result.stdout

    def test_eval_help(self):
        result = subprocess.run(
            [sys.executable, "-m", "rqg.cli", "eval", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "cases" in result.stdout.lower() or "CASES" in result.stdout


class TestCLIParserContract:
    """Guard public CLI flags used by docs, CI templates, and downstream scripts."""

    def test_eval_option_contract(self):
        options = _subparser_option_strings("eval")

        assert {
            "--pack",
            "--docs",
            "--index-dir",
            "--log-dir",
            "--reset-log-dir",
            "--context-k",
            "--mock",
            "--rag-endpoint",
            "--rag-api-key-env",
            "--adapter-config",
        }.issubset(options)

    def test_gate_option_contract(self):
        options = _subparser_option_strings("gate")

        assert {
            "--pack",
            "--docs",
            "--index-dir",
            "--log-dir",
            "--reset-log-dir",
            "--context-k",
            "--mock",
            "--rag-endpoint",
            "--rag-api-key-env",
            "--adapter-config",
            "--config",
            "--days",
            "--aggregation-policy",
            "--baseline-dir",
            "--baseline-days",
            "--cases-file",
            "--quality-pack",
            "--s1-threshold",
            "--overall-threshold",
            "--max-overall-drop-pct",
            "--max-s1-drop-pct",
            "--output-file",
            "--decision-file",
            "--bundle-file",
            "--dry-run",
            "--warn-exit-code",
        }.issubset(options)

    def test_check_option_contract(self):
        options = _subparser_option_strings("check")

        assert {
            "--pack",
            "--log-dir",
            "--config",
            "--days",
            "--aggregation-policy",
            "--baseline-dir",
            "--baseline-days",
            "--cases-file",
            "--quality-pack",
            "--s1-threshold",
            "--overall-threshold",
            "--max-overall-drop-pct",
            "--max-s1-drop-pct",
            "--output-file",
            "--decision-file",
            "--bundle-file",
            "--warn-exit-code",
        }.issubset(options)

    def test_pack_validation_option_contract(self):
        options = _subparser_option_strings("validate-pack")

        assert {
            "--pack",
            "--pack-dir",
            "--cases",
            "--gate-config",
            "--quality-pack",
            "--docs-dir",
            "--endpoint",
            "--api-key-env",
            "--required-env",
            "--connection-query",
            "--connection-top-k",
            "--connection-timeout-sec",
            "--output",
        }.issubset(options)

    def test_downstream_review_and_external_contract_options(self):
        assert {
            "--bundle-file",
            "--summary-file",
            "--log-dir",
            "--output",
            "--title-prefix",
            "--title-suffix",
            "--week-start",
            "--label",
        }.issubset(_subparser_option_strings("export-weekly-review"))
        assert {
            "--endpoint",
            "--query",
            "--top-k",
            "--api-key-env",
            "--timeout-sec",
            "--output",
        }.issubset(_subparser_option_strings("validate-connection"))

    def test_gate_and_check_keep_aggregation_policy_choices(self):
        from rqg.cli import build_parser

        parser = build_parser()
        for command, argv in {
            "gate": ["gate", "packs/hr/cases.csv"],
            "check": ["check"],
        }.items():
            args = parser.parse_args([*argv, "--aggregation-policy", "latest_run"])
            assert args.command == command
            assert args.aggregation_policy == "latest_run"

            args = parser.parse_args([*argv, "--aggregation-policy", "window"])
            assert args.command == command
            assert args.aggregation_policy == "window"


class TestCLIParsing:
    """CLI のパースロジックだけをテスト (実行はモック)。"""

    def test_eval_mock_flag(self):
        """--mock フラグがパーサーに認識されるか。"""
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["eval", "cases.csv", "--mock"])
        assert args.mock is True
        assert args.command == "eval"
        assert args.pack is None
        assert args.reset_log_dir is False

    def test_doctor_parse_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["doctor"])
        assert args.command == "doctor"

    def test_doctor_outputs_environment_report(self, monkeypatch, capsys):
        from rqg.cli.doctor import build_doctor_report, cmd_doctor

        monkeypatch.setenv("EMB_MODEL", "local-fallback-hash-embedding")
        report = build_doctor_report()
        assert "RQG Doctor" in report
        assert "- Python:" in report
        assert "- Platform:" in report
        assert "- RQG version:" in report
        assert "- EMB_MODEL: local-fallback-hash-embedding" in report
        assert "- httpx:" in report
        assert "- faiss:" in report
        assert "- sentence_transformers:" in report
        assert "- fastapi:" in report
        assert "- uvicorn:" in report
        assert "Recommended installs" in report
        assert "- base: pip install -e ." in report
        assert '- external: pip install -e ".[external]"' in report
        assert '- embedding: pip install -e ".[embedding]"' in report
        assert '- dev: pip install -e ".[dev]"' in report
        assert '- all: pip install -e ".[all]"' in report

        exit_code = cmd_doctor(SimpleNamespace())
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "RQG Doctor" in captured.out

    def test_doctor_windows_utf8_note(self, monkeypatch):
        from rqg.cli import doctor

        monkeypatch.setattr(doctor.platform, "system", lambda: "Windows")
        report = doctor.build_doctor_report()
        assert "Windows PowerShell UTF-8 setup:" in report
        assert "chcp 65001" in report
        assert "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8" in report
        assert "$OutputEncoding = [System.Text.Encoding]::UTF8" in report

    def test_eval_accepts_pack_option_without_positional_cases(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["eval", "--pack", "packs/hr", "--mock"])
        assert args.command == "eval"
        assert args.cases is None
        assert args.pack == "packs/hr"

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
        assert args.pack is None
        assert args.quality_pack is None
        assert args.bundle_file is None
        assert args.max_overall_drop_pct is None
        assert args.max_s1_drop_pct is None

    def test_history_defaults(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["history"])
        assert args.command == "history"
        assert args.log_dir == "runs/quality"
        assert args.last == 10
        assert args.compare_offset == 1
        assert args.trend_window == 5

    def test_history_custom_compare_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["history", "--compare-offset", "2", "--trend-window", "7"])
        assert args.command == "history"
        assert args.compare_offset == 2
        assert args.trend_window == 7

    def test_export_weekly_review_defaults(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["export-weekly-review"])
        assert args.command == "export-weekly-review"
        assert args.bundle_file is None
        assert args.summary_file is None
        assert args.log_dir == "runs/quality"
        assert args.title_prefix == "[Phase2.5][Weekly Review]"
        assert args.title_suffix == ""
        assert args.week_start is None
        assert args.label is None

    def test_monthly_summary_defaults(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["monthly-summary"])
        assert args.command == "monthly-summary"
        assert args.log_dir == "runs/quality"
        assert args.month is None
        assert args.markdown_output is None
        assert args.json_output is None

    def test_validate_connection_args(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            ["validate-connection", "--endpoint", "https://rag.example.com/search"]
        )
        assert args.command == "validate-connection"
        assert args.endpoint == "https://rag.example.com/search"
        assert args.query == "healthcheck"

    def test_serve_http_rag_defaults(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["serve-http-rag"])
        assert args.command == "serve-http-rag"
        assert args.docs_dir is None
        assert args.index_dir == "index/external-http"
        assert args.host == "127.0.0.1"
        assert args.port == 8011
        assert args.api_key_env is None

    def test_validate_pack_defaults(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["validate-pack", "--pack-dir", "packs/hr"])
        assert args.command == "validate-pack"
        assert args.pack_dir == "packs/hr"
        assert args.cases is None
        assert args.gate_config is None
        assert args.quality_pack is None
        assert args.docs_dir is None
        assert args.endpoint is None
        assert args.api_key_env is None
        assert args.required_env is None
        assert args.connection_query == "healthcheck"

    def test_validate_pack_accepts_pack_alias(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["validate-pack", "--pack", "packs/hr"])
        assert args.command == "validate-pack"
        assert args.pack_dir == "packs/hr"

    def test_serve_dashboard_defaults(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["serve-dashboard"])
        assert args.command == "serve-dashboard"
        assert args.workspace_dir == "."
        assert args.runs_dir is None
        assert args.host == "127.0.0.1"
        assert args.port == 8012

    def test_gate_defaults(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["gate", "packs/hr/cases.csv"])
        assert args.command == "gate"
        assert args.cases == "packs/hr/cases.csv"
        assert args.pack is None
        assert args.log_dir == "runs/quality"
        assert args.cases_file is None
        assert args.bundle_file is None
        assert args.dry_run is False
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
                "--use-llm-answer-drafts",
            ]
        )
        assert args.command == "gen-cases"
        assert args.mode == "hybrid"
        assert args.use_llm is True
        assert args.use_llm_answer_drafts is True

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

    def test_eval_pack_resolves_cases_and_docs(self, tmp_path):
        pack_dir = _create_pack_dir(tmp_path)

        with patch("rqg.cli.cmd_eval", return_value=0) as eval_mock:
            exit_code = main(["eval", "--pack", str(pack_dir), "--mock"])

        assert exit_code == 0
        resolved_args = eval_mock.call_args.args[0]
        assert resolved_args.cases == (pack_dir / "cases.csv").as_posix()
        assert resolved_args.docs == (pack_dir / "documents").as_posix()
        assert resolved_args.pack == str(pack_dir)

    def test_eval_pack_keeps_explicit_cases_and_docs(self, tmp_path):
        pack_dir = _create_pack_dir(tmp_path)

        with patch("rqg.cli.cmd_eval", return_value=0) as eval_mock:
            exit_code = main(
                [
                    "eval",
                    "custom-cases.csv",
                    "--docs",
                    "custom-docs",
                    "--pack",
                    str(pack_dir),
                    "--mock",
                ]
            )

        assert exit_code == 0
        resolved_args = eval_mock.call_args.args[0]
        assert resolved_args.cases == "custom-cases.csv"
        assert resolved_args.docs == "custom-docs"

    def test_check_pack_resolves_cases_config_and_quality_pack(self, tmp_path):
        pack_dir = _create_pack_dir(tmp_path)

        with patch("rqg.cli.cmd_check", return_value=0) as check_mock:
            exit_code = main(["check", "--pack", str(pack_dir), "--log-dir", "runs/test-pack"])

        assert exit_code == 0
        resolved_args = check_mock.call_args.args[0]
        assert resolved_args.cases_file == (pack_dir / "cases.csv").as_posix()
        assert resolved_args.config == (pack_dir / "gate.yml").as_posix()
        assert resolved_args.quality_pack == (pack_dir / "quality-pack.yml").as_posix()

    def test_gate_pack_resolves_cases_docs_config_and_quality_pack(self, tmp_path):
        pack_dir = _create_pack_dir(tmp_path)

        with patch("rqg.cli.cmd_gate", return_value=0) as gate_mock:
            exit_code = main(["gate", "--pack", str(pack_dir), "--mock"])

        assert exit_code == 0
        resolved_args = gate_mock.call_args.args[0]
        assert resolved_args.cases == (pack_dir / "cases.csv").as_posix()
        assert resolved_args.docs == (pack_dir / "documents").as_posix()
        assert resolved_args.config == (pack_dir / "gate.yml").as_posix()
        assert resolved_args.quality_pack == (pack_dir / "quality-pack.yml").as_posix()

    def test_eval_pack_reports_missing_cases_file(self, tmp_path, capsys):
        pack_dir = _create_pack_dir(tmp_path, include_cases=False)

        with patch("rqg.cli.cmd_eval") as eval_mock:
            exit_code = main(["eval", "--pack", str(pack_dir), "--mock"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "missing required cases.csv" in captured.err
        eval_mock.assert_not_called()

    def test_check_pack_reports_missing_quality_pack(self, tmp_path, capsys):
        pack_dir = _create_pack_dir(tmp_path, include_quality_pack=False)

        with patch("rqg.cli.cmd_check") as check_mock:
            exit_code = main(["check", "--pack", str(pack_dir)])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "missing required quality-pack.yml" in captured.err
        check_mock.assert_not_called()

    def test_gate_pack_reports_missing_documents_dir(self, tmp_path, capsys):
        pack_dir = _create_pack_dir(tmp_path, include_docs=False)

        with patch("rqg.cli.cmd_gate") as gate_mock:
            exit_code = main(["gate", "--pack", str(pack_dir), "--mock"])

        captured = capsys.readouterr()
        assert exit_code == 1
        assert "missing required documents/" in captured.err
        gate_mock.assert_not_called()

    def test_eval_old_style_args_still_work_without_pack(self):
        with patch("rqg.cli.cmd_eval", return_value=0) as eval_mock:
            exit_code = main(["eval", "packs/hr/cases.csv", "--docs", "packs/hr/documents", "--mock"])

        assert exit_code == 0
        resolved_args = eval_mock.call_args.args[0]
        assert resolved_args.cases == "packs/hr/cases.csv"
        assert resolved_args.docs == "packs/hr/documents"
        assert resolved_args.pack is None

    def test_gate_rejects_index_dir_under_runs_before_eval_and_check(self, capsys):
        with patch("rqg.cli.gate.cmd_eval") as eval_mock:
            with patch("rqg.cli.gate.cmd_check") as check_mock:
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
        with patch("rqg.cli.gate.cmd_eval", return_value=1) as eval_mock:
            with patch("rqg.cli.gate.cmd_check", return_value=0) as check_mock:
                exit_code = main(["gate", "packs/hr/cases.csv", "--mock"])

        assert exit_code == 0
        eval_mock.assert_called_once()
        check_mock.assert_called_once()
        check_args = check_mock.call_args.args[0]
        assert check_args.log_dir == "runs/quality"
        assert check_args.cases_file == "packs/hr/cases.csv"

    def test_gate_allows_cases_file_override(self):
        with patch("rqg.cli.gate.cmd_eval", return_value=0):
            with patch("rqg.cli.gate.cmd_check", return_value=1) as check_mock:
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
        with patch("rqg.cli.gate.cmd_eval", return_value=0) as eval_mock:
            with patch("rqg.cli.gate.cmd_check", return_value=0):
                exit_code = main(["gate", "packs/hr/cases.csv", "--reset-log-dir"])

        assert exit_code == 0
        eval_args = eval_mock.call_args.args[0]
        assert eval_args.reset_log_dir is True

    def test_gate_dry_run_uses_isolated_log_dir_and_disables_history_append(self):
        with patch("rqg.cli.gate.cmd_eval", return_value=0) as eval_mock:
            with patch("rqg.cli.gate.cmd_check", return_value=0) as check_mock:
                exit_code = main(["gate", "packs/hr/cases.csv", "--dry-run", "--mock"])

        assert exit_code == 0
        eval_args = eval_mock.call_args.args[0]
        check_args = check_mock.call_args.args[0]
        assert "dry-run" in eval_args.log_dir
        assert eval_args.log_dir == check_args.log_dir
        assert check_args.append_history is False
        assert check_args.notifications_enabled is False

    def test_eval_with_reset_log_dir_cleans_previous_artifacts(self):
        log_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-reset-logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        dry_run_dir = log_dir / "dry-run" / "old-run"
        dry_run_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "20260101.jsonl").write_text("{}\n", encoding="utf-8")
        (log_dir / "gate-report.md").write_text("old", encoding="utf-8")
        (log_dir / "gate-report.json").write_text("{}", encoding="utf-8")
        (log_dir / "gate-decision.json").write_text("{}", encoding="utf-8")
        (log_dir / "gate-decisions.jsonl").write_text("{}\n", encoding="utf-8")
        (dry_run_dir / "gate-report.md").write_text("old", encoding="utf-8")
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
        assert not (log_dir / "gate-report.json").exists()
        assert not (log_dir / "gate-decision.json").exists()
        assert not (log_dir / "gate-decisions.jsonl").exists()
        assert not (log_dir / "dry-run").exists()
        assert (log_dir / "keep.txt").exists()

    def test_eval_runs_only_active_cases(self):
        fake_run = SimpleNamespace(
            run_id="run-active-only",
            total=1,
            passed=1,
            failed=0,
            pass_rate=100.0,
            results=[],
        )
        active_case = QATestCase(
            case_id="active_001",
            name="active case",
            question="Q?",
            status="active",
            severity="S1",
            expected_answer="A",
        )
        draft_case = QATestCase(
            case_id="draft_001",
            name="draft case",
            question="Q?",
            status="draft",
            severity="S2",
            expected_answer="A",
        )
        deprecated_case = QATestCase(
            case_id="deprecated_001",
            name="deprecated case",
            question="Q?",
            status="deprecated",
            severity="S2",
            expected_answer="A",
        )

        with patch(
            "rqg.quality.loader.load_cases",
            return_value=[active_case, draft_case, deprecated_case],
        ):
            with patch("rqg.serving.rag.RAGStore") as store_cls:
                store_cls.return_value.index = object()
                with patch("rqg.quality.runner.RAGQualityRunner") as runner_cls:
                    runner_cls.return_value.run_all.return_value = fake_run
                    runner_cls.save_jsonl.return_value = (
                        Path("tests/.tmp") / f"{uuid.uuid4()}-active-only.jsonl"
                    )

                    exit_code = main(["eval", "packs/hr/cases.csv", "--mock"])

        assert exit_code == 0
        run_cases = runner_cls.return_value.run_all.call_args.args[0]
        saved_cases = runner_cls.save_jsonl.call_args.args[1]
        assert [case.case_id for case in run_cases] == ["active_001"]
        assert [case.case_id for case in saved_cases] == ["active_001"]

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
        quality_pack = (target / "quality-pack.yml").read_text(encoding="utf-8")
        assert "pack_name:" in quality_pack
        assert "created_from_template: true" in quality_pack

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
        assert row["eval_mode"] == "evidence_keyword"
        assert row["severity"] == "S2"
        assert row["expected_evidence"].endswith("#sec-1")
        assert row["expected_keywords"]
        assert row["source_doc"] == "snapshot-001"

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
        assert args.gate_config is None

    def test_validate_cases_parse_gate_config_arg(self):
        from rqg.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(
            [
                "validate-cases",
                "--cases",
                "packs/hr/cases.csv",
                "--gate-config",
                "packs/hr/gate.yml",
            ]
        )
        assert args.command == "validate-cases"
        assert args.gate_config == "packs/hr/gate.yml"

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

    def test_validate_cases_infers_gate_config_and_requires_owner_for_staleness_enabled_pack(self):
        tmp_dir = Path("tests/.tmp") / f"{uuid.uuid4()}-validate-cases-stale"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        csv_path = tmp_dir / "cases.csv"
        self._write_csv(
            csv_path,
            [
                {
                    "case_id": "c001",
                    "question": "What is X?",
                    "expected_answer": "X is Y.",
                    "status": "active",
                    "severity": "S1",
                    "owner": "",
                }
            ],
        )
        (tmp_dir / "gate.yml").write_text(
            "thresholds:\n  case_staleness_days: 30\n  min_fresh_case_review_rate: 100.0\n",
            encoding="utf-8",
        )

        assert main(["validate-cases", "--cases", str(csv_path)]) == 1


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
            [
                "merge-cases",
                "--cases",
                "a.csv",
                "--review",
                "b.csv",
                "--output",
                "c.csv",
                "--no-validate",
            ]
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
            [
                {
                    "case_id": "c_bad",
                    "question": "",
                    "expected_answer": "",
                    "status": "INVALID_STATUS",
                }
            ],
        )

        rc = main(
            [
                "merge-cases",
                "--cases",
                str(base_path),
                "--review",
                str(review_path),
                "--output",
                str(output_path),
            ]
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
            [
                {
                    "case_id": "c_bad",
                    "question": "",
                    "expected_answer": "",
                    "status": "INVALID_STATUS",
                }
            ],
        )

        rc = main(
            [
                "merge-cases",
                "--cases",
                str(base_path),
                "--review",
                str(review_path),
                "--output",
                str(output_path),
                "--no-validate",
            ]
        )
        assert rc == 0
        assert output_path.exists()


def test_merge_cases_skips_high_priority_mixed_review_rows(capsys):
    base_path = Path("tests/.tmp") / f"{uuid.uuid4()}-base.csv"
    review_path = Path("tests/.tmp") / f"{uuid.uuid4()}-review.csv"
    output_path = Path("tests/.tmp") / f"{uuid.uuid4()}-out.csv"

    with open(base_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "question", "expected_answer", "status"])
        writer.writeheader()
        writer.writerow(
            {"case_id": "base_001", "question": "Q?", "expected_answer": "A", "status": "active"}
        )

    with open(review_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["title", "question", "expected_evidence", "expected_keywords", "notes"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "title": "expense_001",
                    "question": "締め日と提出方法はいつまでに対応する必要がありますか？",
                    "expected_evidence": "packs/hr/documents/経費精算ガイドライン.md#sec-1-1",
                    "expected_keywords": "締め日;提出方法",
                    "notes": "mixed_question:deadline,procedure; manual_review_priority:high",
                },
                {
                    "title": "expense_002",
                    "question": "締め日はいつですか？",
                    "expected_evidence": "packs/hr/documents/経費精算ガイドライン.md#sec-1-1",
                    "expected_keywords": "締め日;25日",
                    "notes": "split_candidate_from:締め日と提出方法はいつまでに対応する必要がありますか; manual_review_priority:medium",
                },
            ]
        )

    rc = main(
        [
            "merge-cases",
            "--cases",
            str(base_path),
            "--review",
            str(review_path),
            "--output",
            str(output_path),
            "--no-validate",
        ]
    )

    assert rc == 0
    rows = list(csv.DictReader(output_path.open("r", encoding="utf-8", newline="")))
    assert [row["case_id"] for row in rows] == ["base_001", "expense_002"]
    out = capsys.readouterr().out
    assert "Skipped high-priority mixed review cases: 1" in out
    assert "expense_001" in out
