from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from rqg.cli import main


def _write_pack(
    pack_dir: Path,
    *,
    with_docs: bool = True,
    with_quality_pack: bool = True,
    owner: str = "hr",
    staleness_enabled: bool = False,
) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    gate_lines = [
        "thresholds:",
        "  s1_pass_rate: 100.0",
        "  overall_pass_rate: 85.0",
    ]
    if staleness_enabled:
        gate_lines.extend(
            [
                "  case_staleness_days: 30",
                "  min_fresh_case_review_rate: 100.0",
                "  fresh_case_review_rate_warn: 100.0",
            ]
        )
    (pack_dir / "gate.yml").write_text("\n".join(gate_lines) + "\n", encoding="utf-8")
    if with_quality_pack:
        (pack_dir / "quality-pack.yml").write_text(
            "\n".join(
                [
                    "pack:",
                    "  name: sample-pack",
                    "  review_steward: ops-team",
                    "  pack_name: sample-pack",
                    "  tenant_name: tenant-a",
                    "  use_case: hr-faq",
                    "  vertical: hr",
                    "  risk_profile: high",
                    "  owner: ops-team",
                    "  environment: poc",
                    "  pack_version: '1.0'",
                    "  source_pack: demo_cycle",
                    "  created_from_template: true",
                    "cases_file: cases.csv",
                    "documents_dir: documents",
                    "gate_file: gate.yml",
                    "common_failure_patterns:",
                    "  - name: retrieval_miss",
                    '    first_action: "Review retrieval settings"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    (pack_dir / "cases.csv").write_text(
        "\n".join(
            [
                "case_id,name,status,severity,eval_mode,question,expected_answer,expected_evidence,expected_keywords,category,source_doc,owner,min_case_score,updated_at,last_reviewed_at,notes",
                f"HR001,Leave request timing,active,S1,evidence_keyword,How many days in advance must leave be requested?,,leave_policy.md#sec-1,5 business days;advance,policy,leave_policy.md,{owner},100,2026-04-21,2026-04-21,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    if with_docs:
        docs_dir = pack_dir / "documents"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "leave_policy.md").write_text(
            "Paid leave requests must be submitted 5 business days in advance.\n",
            encoding="utf-8",
        )


def _replace_cases(
    pack_dir: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None
) -> None:
    import csv

    fieldnames = fieldnames or [
        "case_id",
        "name",
        "status",
        "severity",
        "eval_mode",
        "question",
        "expected_answer",
        "expected_evidence",
        "expected_keywords",
        "category",
        "source_doc",
        "owner",
        "min_case_score",
        "updated_at",
        "last_reviewed_at",
        "notes",
    ]
    with (pack_dir / "cases.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_validate_pack_local_docs_success_writes_json(tmp_path, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir)
    output_path = tmp_path / "pack-validation.json"

    exit_code = main(
        [
            "validate-pack",
            "--pack-dir",
            str(pack_dir),
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Pack onboarding validation: OK" in captured.out
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["mode"] == "local_docs"
    assert payload["cases"]["case_count"] == 1
    assert payload["docs"]["file_count"] == 1
    assert payload["quality_pack"]["pack_metadata"]["pack_name"] == "sample-pack"


def test_validate_pack_requires_docs_or_endpoint(tmp_path, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir, with_docs=False)

    exit_code = main(["validate-pack", "--pack-dir", str(pack_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "provide a documents directory or --endpoint" in captured.out


def test_validate_pack_external_mode_requires_api_key_env(tmp_path, monkeypatch, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir, with_docs=False)
    monkeypatch.delenv("RQG_API_KEY", raising=False)

    exit_code = main(
        [
            "validate-pack",
            "--pack-dir",
            str(pack_dir),
            "--endpoint",
            "https://rag.example.com/search",
            "--api-key-env",
            "RQG_API_KEY",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "required environment variable is not set: RQG_API_KEY" in captured.out


def test_validate_pack_external_mode_runs_connection_check(tmp_path, monkeypatch, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir, with_docs=False)
    monkeypatch.setenv("RQG_API_KEY", "secret")

    with patch("rqg.quality.onboarding.validate_http_rag_connection") as mock_validate:
        mock_validate.return_value.model_dump.return_value = {
            "endpoint": "https://rag.example.com/search",
            "query": "healthcheck",
            "top_k": 3,
            "ok": True,
            "error_type": "none",
            "latency_ms": 12.3,
            "chunk_count": 2,
            "sample_chunk_ids": ["chunk-1"],
            "sample_sources": ["policy.md"],
            "issues": [],
            "checked_at": "2026-04-21T00:00:00Z",
        }
        mock_validate.return_value.ok = True

        exit_code = main(
            [
                "validate-pack",
                "--pack-dir",
                str(pack_dir),
                "--endpoint",
                "https://rag.example.com/search",
                "--api-key-env",
                "RQG_API_KEY",
            ]
        )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Pack onboarding validation: OK" in captured.out
    assert "External connection: OK" in captured.out


def test_validate_pack_requires_active_case_owner_when_staleness_enabled(tmp_path, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir, owner="", staleness_enabled=True)

    exit_code = main(["validate-pack", "--pack-dir", str(pack_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "active case owner is required when staleness policy is enabled" in captured.out
    assert "Why it matters:" in captured.out
    assert "owner=hr-ops" in captured.out


def test_validate_pack_explains_missing_expected_answer(tmp_path, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir)
    _replace_cases(
        pack_dir,
        [
            {
                "case_id": "HR002",
                "name": "Leave answer",
                "status": "active",
                "severity": "S2",
                "eval_mode": "exact",
                "question": "When must leave be requested?",
                "expected_answer": "",
                "expected_evidence": "leave_policy.md#sec-1",
                "expected_keywords": "paid leave;advance",
                "category": "policy",
                "source_doc": "leave_policy.md",
                "owner": "hr",
                "min_case_score": "85",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            }
        ],
    )

    exit_code = main(["validate-pack", "--pack-dir", str(pack_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "expected_answer is missing" in captured.out
    assert "Why it matters:" in captured.out
    assert "expected_answer=Paid leave requests" in captured.out


def test_validate_pack_explains_missing_and_too_few_expected_keywords(tmp_path, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir)
    _replace_cases(
        pack_dir,
        [
            {
                "case_id": "HR003",
                "name": "Missing keywords",
                "status": "active",
                "severity": "S2",
                "eval_mode": "evidence_keyword",
                "question": "When must leave be requested?",
                "expected_answer": "",
                "expected_evidence": "leave_policy.md#sec-1",
                "expected_keywords": "",
                "category": "policy",
                "source_doc": "leave_policy.md",
                "owner": "hr",
                "min_case_score": "85",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            },
            {
                "case_id": "HR004",
                "name": "Too few keywords",
                "status": "active",
                "severity": "S2",
                "eval_mode": "evidence_keyword",
                "question": "When must leave be requested?",
                "expected_answer": "",
                "expected_evidence": "leave_policy.md#sec-1",
                "expected_keywords": "deadline",
                "category": "policy",
                "source_doc": "leave_policy.md",
                "owner": "hr",
                "min_case_score": "85",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            },
        ],
    )

    exit_code = main(["validate-pack", "--pack-dir", str(pack_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "expected_keywords is missing" in captured.out
    assert "expected_keywords has fewer than 2 terms" in captured.out
    assert "expected_keywords=deadline;5 business days;advance request" in captured.out


def test_validate_pack_warns_s1_without_evidence_and_unknown_severity(tmp_path, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir)
    _replace_cases(
        pack_dir,
        [
            {
                "case_id": "HR005",
                "name": "S1 missing evidence",
                "status": "active",
                "severity": "S1",
                "eval_mode": "exact",
                "question": "When must leave be requested?",
                "expected_answer": "5 business days in advance.",
                "expected_evidence": "",
                "expected_keywords": "",
                "category": "policy",
                "source_doc": "",
                "owner": "hr",
                "min_case_score": "100",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            },
            {
                "case_id": "HR006",
                "name": "Bad severity",
                "status": "active",
                "severity": "S3",
                "eval_mode": "exact",
                "question": "When must leave be requested?",
                "expected_answer": "5 business days in advance.",
                "expected_evidence": "leave_policy.md#sec-1",
                "expected_keywords": "",
                "category": "policy",
                "source_doc": "leave_policy.md",
                "owner": "hr",
                "min_case_score": "100",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            },
        ],
    )

    exit_code = main(["validate-pack", "--pack-dir", str(pack_dir)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "S1 case has no expected_evidence" in captured.out
    assert "Unknown severity" in captured.out
    assert "severity=S1" in captured.out


def test_validate_pack_warns_legacy_alias_usage(tmp_path, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir)
    _replace_cases(
        pack_dir,
        [
            {
                "case_id": "HR007",
                "name": "Legacy aliases",
                "status": "active",
                "severity": "S1",
                "eval_mode": "evidence_keyword",
                "question": "When must leave be requested?",
                "golden_answer": "",
                "expected_chunks": "leave_policy.md#sec-1",
                "expected_keywords": "paid leave;advance",
                "category": "policy",
                "source_doc": "leave_policy.md",
                "owner": "hr",
                "min_pass_rate": "100",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            }
        ],
        fieldnames=[
            "case_id",
            "name",
            "status",
            "severity",
            "eval_mode",
            "question",
            "golden_answer",
            "expected_chunks",
            "expected_keywords",
            "category",
            "source_doc",
            "owner",
            "min_pass_rate",
            "updated_at",
            "last_reviewed_at",
            "notes",
        ],
    )

    exit_code = main(["validate-pack", "--pack-dir", str(pack_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "legacy alias 'expected_chunks' is still used" in captured.out
    assert "Rename 'expected_chunks' to 'expected_evidence'" in captured.out


def test_validate_pack_warns_s1_field_completeness(tmp_path, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir)
    _replace_cases(
        pack_dir,
        [
            {
                "case_id": "HR008",
                "name": "S1 incomplete",
                "status": "active",
                "severity": "S1",
                "eval_mode": "grounded_judge",
                "question": "When must leave be requested?",
                "expected_answer": "",
                "expected_evidence": "leave_policy.md#sec-1",
                "expected_keywords": "",
                "category": "deadline",
                "source_doc": "leave_policy.md",
                "owner": "hr",
                "min_case_score": "100",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            }
        ],
    )

    exit_code = main(["validate-pack", "--pack-dir", str(pack_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "S1 case has no expected_answer" in captured.out
    assert "S1 case has no expected_keywords" in captured.out


def test_validate_pack_warns_severity_distribution_and_category_skew(tmp_path, capsys) -> None:
    pack_dir = tmp_path / "pack"
    _write_pack(pack_dir)
    rows = []
    for index in range(1, 6):
        rows.append(
            {
                "case_id": f"HR1{index:02d}",
                "name": f"S2 case {index}",
                "status": "active",
                "severity": "S2",
                "eval_mode": "evidence_keyword",
                "question": f"What is policy item {index}?",
                "expected_answer": "",
                "expected_evidence": "leave_policy.md#sec-1",
                "expected_keywords": "paid leave;advance",
                "category": "deadline",
                "source_doc": "leave_policy.md",
                "owner": "hr",
                "min_case_score": "85",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            }
        )
    _replace_cases(pack_dir, rows)

    exit_code = main(["validate-pack", "--pack-dir", str(pack_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Quality Pack has 0 active S1 cases" in captured.out
    assert "All active cases are S2" in captured.out
    assert "Category coverage is concentrated in 'deadline'" in captured.out


def test_validate_pack_warns_all_s1_and_too_few_s1(tmp_path, capsys) -> None:
    all_s1_pack = tmp_path / "all-s1"
    _write_pack(all_s1_pack)
    _replace_cases(
        all_s1_pack,
        [
            {
                "case_id": "HR201",
                "name": "S1 case 1",
                "status": "active",
                "severity": "S1",
                "eval_mode": "evidence_keyword",
                "question": "What is policy item 1?",
                "expected_answer": "Answer 1.",
                "expected_evidence": "leave_policy.md#sec-1",
                "expected_keywords": "paid leave;advance",
                "category": "deadline",
                "source_doc": "leave_policy.md",
                "owner": "hr",
                "min_case_score": "100",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            },
            {
                "case_id": "HR202",
                "name": "S1 case 2",
                "status": "active",
                "severity": "S1",
                "eval_mode": "evidence_keyword",
                "question": "What is policy item 2?",
                "expected_answer": "Answer 2.",
                "expected_evidence": "leave_policy.md#sec-1",
                "expected_keywords": "paid leave;advance",
                "category": "eligibility",
                "source_doc": "leave_policy.md",
                "owner": "hr",
                "min_case_score": "100",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            },
        ],
    )

    all_s1_exit = main(["validate-pack", "--pack-dir", str(all_s1_pack)])
    all_s1_output = capsys.readouterr().out
    assert all_s1_exit == 0
    assert "All active cases are S1" in all_s1_output

    thin_s1_pack = tmp_path / "thin-s1"
    _write_pack(thin_s1_pack)
    rows = []
    for index in range(1, 6):
        rows.append(
            {
                "case_id": f"HR3{index:02d}",
                "name": f"case {index}",
                "status": "active",
                "severity": "S1" if index == 1 else "S2",
                "eval_mode": "evidence_keyword",
                "question": f"What is policy item {index}?",
                "expected_answer": f"Answer {index}.",
                "expected_evidence": "leave_policy.md#sec-1",
                "expected_keywords": "paid leave;advance",
                "category": "deadline" if index < 5 else "eligibility",
                "source_doc": "leave_policy.md",
                "owner": "hr",
                "min_case_score": "100" if index == 1 else "85",
                "updated_at": "2026-04-21",
                "last_reviewed_at": "2026-04-21",
                "notes": "",
            }
        )
    _replace_cases(thin_s1_pack, rows)

    thin_s1_exit = main(["validate-pack", "--pack-dir", str(thin_s1_pack)])
    thin_s1_output = capsys.readouterr().out
    assert thin_s1_exit == 0
    assert "only 1 S1 case across 5 active cases" in thin_s1_output
