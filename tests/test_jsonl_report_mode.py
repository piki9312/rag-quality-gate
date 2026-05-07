from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from rqg.cli.eval import cmd_eval
from rqg.domain import GateDecision
from rqg.quality.check import GateConfig, build_gate_decision, run_check
from rqg.quality.models import EvalResult, EvalRun, QARunRecord, QATestCase
from rqg.quality.runner import RAGQualityRunner

RAW_ANSWER = "Raw answer text with customer specific detail"
EXPECTED_ANSWER = "Expected answer that should not be persisted in non-full mode"
RAW_EVIDENCE = "Retrieved evidence body that should never be in JSONL"


def _case() -> QATestCase:
    return QATestCase(
        case_id="CASE-JSONL-001",
        name="jsonl redaction case",
        question="Question that should not be persisted?",
        severity="S1",
        expected_answer=EXPECTED_ANSWER,
        expected_evidence=["chunk-secret"],
        expected_keywords=["customer"],
        category="security",
    )


def _run(*, answer: str = RAW_ANSWER, passed: bool = False) -> EvalRun:
    result = EvalResult(
        case_id="CASE-JSONL-001",
        severity="S1",
        passed=passed,
        score=1.0 if passed else 0.0,
        answer=answer,
        retrieved_ids=["chunk-secret"],
        failure_type=None if passed else "keyword_miss",
        failure_category=None if passed else "answer_quality",
        failure_reason="" if passed else "Keyword match 0% < 80%",
        answer_match=passed,
        evidence_match=True,
        retrieval_hit=True,
        evidence_recall=1.0,
        faithfulness_score=0.9,
        judge_relevance=0.9,
    )
    return EvalRun(
        run_id="run-jsonl-mode",
        timestamp=datetime.now(timezone.utc),
        results=[result],
    )


def _write_jsonl(tmp_path: Path, *, report_mode: str, passed: bool = False) -> Path:
    return RAGQualityRunner.save_jsonl(
        _run(passed=passed),
        [_case()],
        str(tmp_path),
        report_mode=report_mode,
    )


def _read_single_record(jsonl_path: Path) -> dict:
    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    return json.loads(lines[0])


def test_ci_mode_does_not_persist_raw_answer_in_jsonl(tmp_path) -> None:
    jsonl_path = _write_jsonl(tmp_path, report_mode="ci")
    payload = _read_single_record(jsonl_path)
    payload_text = json.dumps(payload, ensure_ascii=False)

    assert payload["answer"] == "[REDACTED]"
    assert payload["answer_hash"]
    assert payload["answer_present"] is True
    assert payload["answer_redacted"] is True
    assert RAW_ANSWER not in payload_text
    assert EXPECTED_ANSWER not in payload_text
    assert RAW_EVIDENCE not in payload_text
    assert "ai_answer" not in payload_text
    assert "retrieved_evidence" not in payload_text
    assert "chunk_text" not in payload_text
    assert "source_path" not in payload_text


def test_redacted_mode_redacts_answer_in_jsonl(tmp_path) -> None:
    jsonl_path = _write_jsonl(tmp_path, report_mode="redacted")
    payload = _read_single_record(jsonl_path)

    assert payload["answer"] == "[REDACTED]"
    assert payload["answer_hash"]
    assert payload["answer_present"] is True
    assert payload["answer_redacted"] is True
    assert RAW_ANSWER not in json.dumps(payload, ensure_ascii=False)


def test_full_mode_preserves_raw_answer_locally(tmp_path) -> None:
    jsonl_path = _write_jsonl(tmp_path, report_mode="full", passed=True)
    payload = _read_single_record(jsonl_path)

    assert payload["answer"] == RAW_ANSWER
    assert payload["answer_hash"]
    assert payload["answer_present"] is True
    assert payload["answer_redacted"] is False


def test_check_can_read_redacted_jsonl(tmp_path) -> None:
    _write_jsonl(tmp_path, report_mode="redacted")

    result = run_check(str(tmp_path), GateConfig(s1_pass_rate=100.0, overall_pass_rate=80.0))

    assert result.gate_status == "fail"
    assert result.current_runs == 1
    assert result.s1_total == 1
    assert result.s1_passed == 0
    assert result.failure_categories["answer_quality"] == 1


def test_existing_gate_decision_contract_unchanged(tmp_path) -> None:
    _write_jsonl(tmp_path, report_mode="ci")
    result = run_check(str(tmp_path), GateConfig(s1_pass_rate=100.0, overall_pass_rate=80.0))

    decision = build_gate_decision(result)
    payload = decision.model_dump(mode="json")

    assert isinstance(decision, GateDecision)
    assert set(
        [
            "run_id",
            "status",
            "policy_status",
            "reasons",
            "reason_codes",
            "metrics",
            "next_actions",
            "needs_human_review",
            "created_at",
        ]
    ).issubset(payload)


def test_eval_full_report_mode_fails_in_github_actions(monkeypatch, capsys) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    exit_code = cmd_eval(SimpleNamespace(report_mode="full"))

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "--report-mode full is not allowed" in captured.err
    assert "local/private runner" in captured.err
