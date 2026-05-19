# Contributing

## Local Setup

Install the development dependencies before working on Python changes:

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

## Before Opening A PR

Run the same formatter checks that CI runs:

```powershell
.\.venv\Scripts\python scripts\dev_check.py lint
```

To format Python files before checking:

```powershell
.\.venv\Scripts\python scripts\dev_check.py format
```

To run formatting checks and tests together:

```powershell
.\.venv\Scripts\python scripts\dev_check.py check
```

The CI formatting gate currently checks:

```powershell
.\.venv\Scripts\python -m black --check src tests
.\.venv\Scripts\python -m isort --check-only src tests
```

Black uses `line-length = 100` and `target-version = ["py311"]` from
`pyproject.toml`. isort uses the Black profile with the same line length.

## Pre-Commit

This repository includes `.pre-commit-config.yaml` for Black and isort. Install
the hook after installing development dependencies:

```powershell
.\.venv\Scripts\python -m pre_commit install
```

You can also run all hooks manually:

```powershell
.\.venv\Scripts\python -m pre_commit run --all-files
```

## Windows Notes

Use `python -m ...` through the virtual environment so the formatter versions
come from this repository's development dependencies instead of a global Python
installation.
