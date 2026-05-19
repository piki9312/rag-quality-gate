from __future__ import annotations

import argparse
import subprocess
import sys

CHECK_PATHS = ("src", "tests")


def run_command(args: list[str]) -> int:
    print("+ " + " ".join(args), flush=True)
    return subprocess.run(args, check=False).returncode


def run_many(commands: list[list[str]]) -> int:
    for command in commands:
        return_code = run_command(command)
        if return_code:
            return return_code
    return 0


def format_commands() -> list[list[str]]:
    return [
        [sys.executable, "-m", "isort", *CHECK_PATHS],
        [sys.executable, "-m", "black", *CHECK_PATHS],
    ]


def lint_commands() -> list[list[str]]:
    return [
        [sys.executable, "-m", "black", "--check", *CHECK_PATHS],
        [sys.executable, "-m", "isort", "--check-only", *CHECK_PATHS],
    ]


def test_commands() -> list[list[str]]:
    return [[sys.executable, "-m", "pytest", "tests"]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local development checks.")
    parser.add_argument(
        "command",
        choices=("format", "lint", "test", "check"),
        help="format rewrites imports/code, lint matches CI format checks, check runs lint then tests.",
    )
    args = parser.parse_args()

    if args.command == "format":
        return run_many(format_commands())
    if args.command == "lint":
        return run_many(lint_commands())
    if args.command == "test":
        return run_many(test_commands())
    return run_many([*lint_commands(), *test_commands()])


if __name__ == "__main__":
    raise SystemExit(main())
