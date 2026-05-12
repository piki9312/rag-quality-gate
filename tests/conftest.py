"""conftest.py — shared fixtures for rag-quality-gate tests."""

from __future__ import annotations

import os
import sys

import pytest

from rqg.quality.models import EvalResult, QATestCase


@pytest.fixture(autouse=True)
def _clear_github_actions_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep CLI default-mode tests stable when pytest itself runs in Actions."""
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


# ------------------------------------------------------------------
# テストケース fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def s1_case() -> QATestCase:
    return QATestCase(
        case_id="QA001",
        name="有給申請期限",
        question="有給休暇の申請期限は？",
        severity="S1",
        expected_keywords=["5営業日前", "申請"],
        expected_evidence=["chunk_A"],
        expected_answer="有給休暇は5営業日前までに申請してください。",
        category="就業規則",
    )


@pytest.fixture()
def s2_case() -> QATestCase:
    return QATestCase(
        case_id="QA002",
        name="経費締め日",
        question="経費精算の締め日はいつですか？",
        severity="S2",
        expected_keywords=["25日", "レシート"],
        expected_evidence=[],
        category="経費精算",
    )


@pytest.fixture()
def passed_result() -> EvalResult:
    return EvalResult(
        case_id="QA001",
        severity="S1",
        passed=True,
        score=1.0,
        answer="5営業日前までに申請してください。",
        retrieved_ids=["chunk_A", "chunk_B"],
        latency_ms=120.0,
        retrieval_hit=True,
        evidence_recall=1.0,
        faithfulness_score=0.9,
        judge_relevance=0.8,
    )


@pytest.fixture()
def failed_result() -> EvalResult:
    return EvalResult(
        case_id="QA002",
        severity="S2",
        passed=False,
        score=0.3,
        answer="わかりません。",
        failure_type="keyword_miss",
        failure_reason="Keyword match 0% < 50%",
        latency_ms=90.0,
    )
