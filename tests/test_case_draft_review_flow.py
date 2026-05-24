from __future__ import annotations

import csv
import json
import shutil
import uuid
from pathlib import Path

import pytest
import yaml

from rqg.case_draft import (
    approve_reviewed_cases,
    build_review_cases_payload,
    export_case_review_artifacts,
    load_review_cases_yaml,
    render_review_cases_markdown,
)
from rqg.cli import main
from rqg.quality.case_schema import FORMAL_CASE_FIELDS
from rqg.quality.loader import filter_cases_by_status, load_cases


def _workspace_tmp() -> Path:
    root = Path("tests/.tmp") / f"case-draft-review-flow-{uuid.uuid4()}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _draft_rows() -> list[dict[str, str]]:
    return [
        {
            "case_id": "draft_hr_deadline_001",
            "name": "休暇申請期限の確認",
            "status": "needs_review",
            "severity": "S1",
            "eval_mode": "evidence_keyword",
            "question": "休暇申請はいつまでに必要ですか？",
            "expected_answer": "draft answer",
            "expected_evidence": "leave_policy.md#deadline",
            "expected_keywords": "deadline",
            "category": "deadline_check",
            "source_doc": "leave_policy.md",
            "owner": "",
            "min_case_score": "100",
            "updated_at": "2026-05-24",
            "last_reviewed_at": "",
            "notes": (
                "generated_by:case_draft_engine; case_type:generated-draft; "
                "answer_status:unapproved-draft; intent:deadline_check; "
                "failure_pattern:deadline_or_period_mismatch"
            ),
        },
        {
            "case_id": "draft_hr_pending_002",
            "name": "pending case",
            "status": "needs_review",
            "severity": "S2",
            "eval_mode": "grounded_judge",
            "question": "pending?",
            "expected_answer": "pending draft",
            "expected_evidence": "leave_policy.md#pending",
            "expected_keywords": "",
            "category": "policy",
            "source_doc": "leave_policy.md",
            "owner": "",
            "min_case_score": "85",
            "updated_at": "2026-05-24",
            "last_reviewed_at": "",
            "notes": "generated_by:case_draft_engine",
        },
        {
            "case_id": "draft_hr_reject_003",
            "name": "reject case",
            "status": "needs_review",
            "severity": "S2",
            "eval_mode": "grounded_judge",
            "question": "reject?",
            "expected_answer": "reject draft",
            "expected_evidence": "leave_policy.md#reject",
            "expected_keywords": "",
            "category": "policy",
            "source_doc": "leave_policy.md",
            "owner": "",
            "min_case_score": "85",
            "updated_at": "2026-05-24",
            "last_reviewed_at": "",
            "notes": "generated_by:case_draft_engine",
        },
    ]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FORMAL_CASE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _review_payload() -> dict[str, object]:
    payload = build_review_cases_payload(_draft_rows())
    cases = payload["cases"]
    assert isinstance(cases, list)
    approve_case = cases[0]
    pending_case = cases[1]
    reject_case = cases[2]
    approve_case["decision"] = "approve"
    approve_case["vendor_review"] = {
        "expected_answer": "休暇申請は5営業日前までに必要です。",
        "expected_evidence": ["leave_policy.md#deadline"],
        "expected_keywords": ["5営業日前", "休暇申請"],
        "severity": "S1",
        "eval_mode": "evidence_keyword",
        "reviewed_by": "vendor-reviewer",
        "reviewed_at": "2026-05-24",
        "notes": "vendor confirmed deadline",
    }
    pending_case["decision"] = "pending"
    reject_case["decision"] = "reject"
    return payload


def test_draft_case_exports_review_yaml_and_markdown() -> None:
    root = _workspace_tmp()
    try:
        draft_path = root / "cases_draft.csv"
        yaml_path = root / "review_cases.yaml"
        md_path = root / "review_cases.md"
        _write_csv(draft_path, _draft_rows())

        export_case_review_artifacts(draft_path, output_yaml=yaml_path, output_md=md_path)

        payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        assert payload["version"] == 1
        assert payload["generated_by"] == "proof_gate_review_flow"
        assert payload["cases"][0]["case_id"] == "draft_hr_deadline_001"
        assert payload["cases"][0]["decision"] == "pending"
        assert payload["cases"][0]["status"] == "needs_review"
        assert payload["cases"][0]["suggestion"]["intent"] == "deadline_check"

        markdown = md_path.read_text(encoding="utf-8")
        assert "# ケース下書きレビュー" in markdown
        assert "## draft_hr_deadline_001: 休暇申請期限の確認" in markdown
        assert "ベンダー確認事項:" in markdown
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_render_review_cases_markdown_is_preview_only() -> None:
    markdown = render_review_cases_markdown(build_review_cases_payload(_draft_rows()))

    assert "Markdown" not in markdown
    assert "レビュー判断: pending" in markdown
    assert "期待される回答の型:" in markdown


def test_approve_cases_promotes_only_approved_cases_and_reflects_vendor_review() -> None:
    root = _workspace_tmp()
    try:
        draft_path = root / "cases_draft.csv"
        review_path = root / "review_cases.yaml"
        output_path = root / "cases.csv"
        _write_csv(draft_path, _draft_rows())
        review_path.write_text(
            yaml.safe_dump(_review_payload(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

        approve_reviewed_cases(
            draft_path=draft_path,
            review_path=review_path,
            output_path=output_path,
        )

        rows = _read_csv(output_path)
        by_id = {row["case_id"]: row for row in rows}
        approved = by_id["draft_hr_deadline_001"]
        assert approved["status"] == "active"
        assert approved["expected_answer"] == "休暇申請は5営業日前までに必要です。"
        assert approved["expected_evidence"] == "leave_policy.md#deadline"
        assert approved["expected_keywords"] == "5営業日前;休暇申請"
        assert approved["severity"] == "S1"
        assert approved["eval_mode"] == "evidence_keyword"
        assert approved["last_reviewed_at"] == "2026-05-24"
        assert approved["owner"] == "vendor-reviewer"
        assert "intent:deadline_check" in approved["notes"]
        assert "failure_pattern:deadline_or_period_mismatch" in approved["notes"]
        assert "generated_by:proof_gate_review_flow" in approved["notes"]
        assert "approved_by:vendor-reviewer" in approved["notes"]

        assert by_id["draft_hr_pending_002"]["status"] == "needs_review"
        assert by_id["draft_hr_reject_003"]["status"] == "deprecated"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_gate_execution_target_remains_active_only_after_approval() -> None:
    root = _workspace_tmp()
    try:
        draft_path = root / "cases_draft.csv"
        review_path = root / "review_cases.yaml"
        output_path = root / "cases.csv"
        _write_csv(draft_path, _draft_rows())
        review_path.write_text(
            yaml.safe_dump(_review_payload(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        approve_reviewed_cases(
            draft_path=draft_path,
            review_path=review_path,
            output_path=output_path,
        )

        cases = load_cases(str(output_path))
        active_cases = filter_cases_by_status(cases)

        assert [case.case_id for case in active_cases] == ["draft_hr_deadline_001"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_invalid_review_yaml_schema_errors() -> None:
    root = _workspace_tmp()
    try:
        review_path = root / "review_cases.yaml"
        review_path.write_text(
            yaml.safe_dump({"version": 1, "generated_by": "proof_gate_review_flow"}),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="cases list"):
            load_review_cases_yaml(review_path)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_cli_export_case_review_and_approve_cases() -> None:
    root = _workspace_tmp()
    try:
        draft_path = root / "cases_draft.csv"
        review_path = root / "review_cases.yaml"
        md_path = root / "review_cases.md"
        output_path = root / "cases.csv"
        _write_csv(draft_path, _draft_rows())

        assert (
            main(
                [
                    "export-case-review",
                    "--draft",
                    str(draft_path),
                    "--output-yaml",
                    str(review_path),
                    "--output-md",
                    str(md_path),
                ]
            )
            == 0
        )
        payload = yaml.safe_load(review_path.read_text(encoding="utf-8"))
        payload["cases"][0]["decision"] = "approve"
        payload["cases"][0]["vendor_review"] = _review_payload()["cases"][0]["vendor_review"]
        review_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

        assert (
            main(
                [
                    "approve-cases",
                    "--draft",
                    str(draft_path),
                    "--review",
                    str(review_path),
                    "--output",
                    str(output_path),
                ]
            )
            == 0
        )
        assert output_path.exists()
        rows = _read_csv(output_path)
        assert rows[0]["status"] == "active"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_cli_parser_exposes_case_review_commands() -> None:
    from rqg.cli import build_parser

    parser = build_parser()
    assert (
        parser.parse_args(
            [
                "export-case-review",
                "--draft",
                "cases_draft.csv",
                "--output-yaml",
                "review_cases.yaml",
                "--output-md",
                "review_cases.md",
            ]
        ).command
        == "export-case-review"
    )
    assert (
        parser.parse_args(
            [
                "approve-cases",
                "--draft",
                "cases_draft.csv",
                "--review",
                "review_cases.yaml",
                "--output",
                "cases.csv",
            ]
        ).command
        == "approve-cases"
    )


def test_approve_cases_cli_rejects_invalid_yaml() -> None:
    root = _workspace_tmp()
    try:
        draft_path = root / "cases_draft.csv"
        review_path = root / "bad_review_cases.yaml"
        output_path = root / "cases.csv"
        _write_csv(draft_path, _draft_rows())
        review_path.write_text(json.dumps({"version": 2, "cases": []}), encoding="utf-8")

        assert (
            main(
                [
                    "approve-cases",
                    "--draft",
                    str(draft_path),
                    "--review",
                    str(review_path),
                    "--output",
                    str(output_path),
                ]
            )
            == 1
        )
        assert not output_path.exists()
    finally:
        shutil.rmtree(root, ignore_errors=True)
