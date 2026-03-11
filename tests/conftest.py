"""conftest.py — shared fixtures for rag-quality-gate tests."""

from __future__ import annotations

import os
import sys

import pytest

from rqg.quality.models import EvalResult, QATestCase


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
        expected_chunks=["chunk_A"],
        golden_answer="有給休暇は5営業日前までに申請してください。",
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
        expected_chunks=[],
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
