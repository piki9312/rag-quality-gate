"""Data models for RAG Quality Gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# ------------------------------------------------------------------
# Test Case (input)
# ------------------------------------------------------------------


@dataclass
class QATestCase:
    """1件の品質テストケース。CSV から読み込む。"""

    case_id: str
    name: str
    question: str
    severity: str = "S2"  # S1 | S2
    expected_keywords: list[str] = field(default_factory=list)
    expected_chunks: list[str] = field(default_factory=list)
    golden_answer: str = ""
    category: str = "general"
    owner: str = ""
    min_pass_rate: float = 0.0


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
    retrieval_hit: bool | None = None  # expected chunk が top-k に含まれたか
    faithfulness_score: float | None = None  # 0.0〜1.0


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
    passed: bool = Field(...)
    failure_type: str | None = Field(None)
    failure_category: str | None = Field(None)
    reasons: list[str] = Field(default_factory=list)
    answer: str = Field(default="")
    retrieved_ids: list[str] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0)
    cost_usd: float | None = Field(None)
    token_usage: dict[str, int] | None = Field(None)
    retrieval_hit: bool | None = Field(None)

    model_config = ConfigDict(ser_json_timedelta="float")

    @classmethod
    def from_eval_result(cls, result: EvalResult, run_id: str, case: QATestCase) -> QARunRecord:
        reasons = [result.failure_reason] if result.failure_reason else []
        return cls(
            timestamp=result.timestamp,
            run_id=run_id,
            case_id=result.case_id,
            severity=result.severity,
            category=case.category,
            passed=result.passed,
            failure_type=result.failure_type,
            failure_category=result.failure_category,
            reasons=reasons,
            answer=result.answer,
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
        )
