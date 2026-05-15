"""Data models for RAG Quality Gate."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# ------------------------------------------------------------------
# Test Case (input)
# ------------------------------------------------------------------


@dataclass
class QATestCase:
    """1件の品質テストケース。CSV から読み込む。

    正式スキーマ (cases.csv):
        case_id, name, status, severity, eval_mode, question,
        expected_answer, expected_evidence, expected_keywords,
        category, source_doc, owner, min_case_score, updated_at,
        last_reviewed_at, notes

    旧項目との対応:
        golden_answer   -> expected_answer
        expected_chunks -> expected_evidence
        min_pass_rate   -> min_case_score
    """

    case_id: str
    name: str
    question: str
    severity: str = "S2"  # S1 | S2
    status: str = "active"  # draft | active | needs_review | deprecated
    eval_mode: str = ""  # exact | evidence_keyword | grounded_judge
    expected_answer: str = ""
    expected_evidence: list[str] = field(default_factory=list)
    expected_keywords: list[str] = field(default_factory=list)
    category: str = "general"
    risk_domain: str = ""
    required_action: str = ""
    evidence_required: bool = False
    owner_role: str = ""
    source_doc: str = ""
    owner: str = ""
    min_case_score: float = 0.0
    updated_at: str = ""
    last_reviewed_at: str = ""
    notes: str = ""

    # ------ backward-compat aliases (read-only) ------
    @property
    def golden_answer(self) -> str:
        return self.expected_answer

    @property
    def expected_chunks(self) -> list[str]:
        return self.expected_evidence

    @property
    def min_pass_rate(self) -> float:
        return self.min_case_score


# ------------------------------------------------------------------
# Eval Result (output of a single case execution)
# ------------------------------------------------------------------


@dataclass
class EvalResult:
    """1件のテストケース実行結果。"""

    case_id: str
    severity: str
    passed: bool
    score: float = 0.0
    answer: str = ""
    retrieved_ids: list[str] = field(default_factory=list)
    failure_type: str | None = None
    failure_category: str | None = None
    failure_reason: str = ""
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Retrieval quality
    answer_match: bool | None = None  # expected_keywords の閾値判定を満たしたか
    evidence_match: bool | None = None  # 互換キー: expected_chunks が検索結果に含まれたか
    retrieval_hit: bool | None = None  # expected chunk が top-k に含まれたか
    evidence_recall: float | None = None  # 0.0〜1.0
    faithfulness_score: float | None = None  # 0.0〜1.0
    judge_relevance: float | None = None  # 0.0〜1.0
    judge_fallback_used: bool = False
    judge_fallback_reason: str | None = None
    judge_failure_type: str | None = None
    embedding_fallback_used: bool = False
    embedding_fallback_reason: str | None = None


# ------------------------------------------------------------------
# Eval Run (aggregate)
# ------------------------------------------------------------------


@dataclass
class EvalRun:
    """1回の評価ラン全体のサマリー。"""

    run_id: str
    timestamp: datetime
    results: list[EvalResult]
    total: int = 0
    passed: int = 0
    failed: int = 0

    def __post_init__(self):
        self.total = len(self.results)
        self.passed = sum(1 for r in self.results if r.passed)
        self.failed = self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total else 0.0


# ------------------------------------------------------------------
# Persistent Record (JSONL)
# ------------------------------------------------------------------


class QARunRecord(BaseModel):
    """JSONL 永続化用レコード。"""

    timestamp: datetime = Field(..., description="UTC timestamp")
    run_id: str = Field(...)
    case_id: str = Field(...)
    severity: str = Field(...)
    category: str = Field(default="general")
    risk_domain: str | None = Field(None)
    required_action: str | None = Field(None)
    passed: bool = Field(...)
    failure_type: str | None = Field(None)
    failure_category: str | None = Field(None)
    reasons: list[str] = Field(default_factory=list)
    answer: str = Field(default="")
    answer_hash: str | None = Field(default=None)
    answer_present: bool = Field(default=False)
    answer_redacted: bool = Field(default=False)
    execution_mode: str | None = Field(default=None)
    report_mode: str | None = Field(default=None)
    retrieved_ids: list[str] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0)
    cost_usd: float | None = Field(None)
    token_usage: dict[str, int] | None = Field(None)
    retrieval_hit: bool | None = Field(None)
    answer_match: bool | None = Field(None)
    evidence_match: bool | None = Field(None)
    evidence_recall: float | None = Field(None)
    faithfulness_score: float | None = Field(None)
    judge_relevance: float | None = Field(None)
    judge_fallback_used: bool | None = Field(None)
    judge_fallback_reason: str | None = Field(None)
    judge_failure_type: str | None = Field(None)
    embedding_fallback_used: bool | None = Field(None)
    embedding_fallback_reason: str | None = Field(None)

    model_config = ConfigDict(ser_json_timedelta="float")

    @classmethod
    def from_eval_result(
        cls,
        result: EvalResult,
        run_id: str,
        case: QATestCase,
        *,
        report_mode: str = "full",
        execution_mode: str | None = None,
    ) -> QARunRecord:
        reasons = [result.failure_reason] if result.failure_reason else []
        answer_match = result.answer_match
        if answer_match is None and case.expected_keywords and result.failure_type != "error":
            answer_match = result.failure_type != "keyword_miss"

        evidence_match = result.evidence_match
        if evidence_match is None and case.expected_chunks:
            evidence_match = result.retrieval_hit

        answer = result.answer or ""
        answer_present = bool(answer.strip())
        normalized_report_mode = _normalize_record_report_mode(report_mode)
        answer_hash = _hash_text(answer) if answer_present else None
        answer_redacted = normalized_report_mode != "full"
        persisted_answer = "[REDACTED]" if answer_present and answer_redacted else answer

        return cls(
            timestamp=result.timestamp,
            run_id=run_id,
            case_id=result.case_id,
            severity=result.severity,
            category=case.category,
            risk_domain=case.risk_domain or case.category,
            required_action=case.required_action or _infer_required_action(case.severity),
            passed=result.passed,
            failure_type=result.failure_type,
            failure_category=result.failure_category,
            reasons=reasons,
            answer=persisted_answer,
            answer_hash=answer_hash,
            answer_present=answer_present,
            answer_redacted=answer_redacted,
            execution_mode=execution_mode,
            report_mode=normalized_report_mode,
            retrieved_ids=result.retrieved_ids,
            latency_ms=result.latency_ms,
            cost_usd=result.cost_usd if result.cost_usd > 0 else None,
            token_usage=(
                {
                    "input": result.input_tokens,
                    "output": result.output_tokens,
                    "total": result.total_tokens,
                }
                if result.total_tokens > 0
                else None
            ),
            retrieval_hit=result.retrieval_hit,
            answer_match=answer_match,
            evidence_match=evidence_match,
            evidence_recall=result.evidence_recall,
            faithfulness_score=result.faithfulness_score,
            judge_relevance=result.judge_relevance,
            judge_fallback_used=result.judge_fallback_used or None,
            judge_fallback_reason=result.judge_fallback_reason,
            judge_failure_type=result.judge_failure_type,
            embedding_fallback_used=result.embedding_fallback_used or None,
            embedding_fallback_reason=result.embedding_fallback_reason,
        )


def _normalize_record_report_mode(value: object) -> str:
    normalized = str(value or "full").strip().lower().replace("-", "_")
    if normalized in {"ci", "redacted", "full"}:
        return normalized
    return "full"


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _infer_required_action(severity: str) -> str:
    normalized = str(severity or "").strip().upper()
    if normalized == "S1":
        return "block"
    if normalized == "S2":
        return "allow_with_warning"
    return "allow"
