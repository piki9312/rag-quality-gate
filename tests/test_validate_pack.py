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