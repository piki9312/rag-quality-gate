"""Tests for CLI entry point."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


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
