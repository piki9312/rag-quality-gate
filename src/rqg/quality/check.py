"""Gate check — ベースライン比較 + 閾値判定 → pass/fail。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .aggregate import case_pass_rates, severity_pass_rate
from .models import QARunRecord


# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------


@dataclass
class GateConfig:
    """品質ゲートの閾値設定。"""

    s1_pass_rate: float = 100.0
    overall_pass_rate: float = 80.0
    retrieval_precision_threshold: float = 0.0  # 0 = チェックしない
    max_latency_p95_ms: float = 0.0  # 0 = チェックしない
    max_cost_per_query_usd: float = 0.0

    @classmethod
    def from_yaml(cls, path: str) -> GateConfig:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        th = data.get("thresholds", {})
        return cls(
            s1_pass_rate=th.get("s1_pass_rate", 100.0),
            overall_pass_rate=th.get("overall_pass_rate", 80.0),
            retrieval_precision_threshold=th.get("retrieval_precision", 0.0),
            max_latency_p95_ms=th.get("max_latency_p95_ms", 0.0),
            max_cost_per_query_usd=th.get("max_cost_per_query_usd", 0.0),
        )


# ------------------------------------------------------------------
# Results
# ------------------------------------------------------------------


@dataclass
class ThresholdResult:
    name: str
    threshold: float
    actual: float
    passed: bool
    detail: str = ""


@dataclass
class CheckResult:
    current_runs: int
    baseline_runs: int
    overall_rate: float
    s1_rate: float
    s1_passed: int
    s1_total: int
    thresholds: list[ThresholdResult] = field(default_factory=list)
    case_thresholds: list[ThresholdResult] = field(default_factory=list)

    @property
    def gate_passed(self) -> bool:
        return all(t.passed for t in self.thresholds) and all(
            t.passed for t in self.case_thresholds
        )


# ------------------------------------------------------------------
# JSONL I/O
# ------------------------------------------------------------------


def load_records(log_dir: str, days: int | None = None) -> list[QARunRecord]:
    """JSONL ファイルから QARunRecord を読み込む。"""
    path = Path(log_dir)
    if not path.exists():
        return []

    cutoff = None
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    records: list[QARunRecord] = []
    for f in sorted(path.glob("*.jsonl")):
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = QARunRecord.model_validate_json(line)
                    if cutoff and rec.timestamp < cutoff:
                        continue
                    records.append(rec)
                except Exception:
                    continue
    return records


# ------------------------------------------------------------------
# Gate logic
# ------------------------------------------------------------------


def run_check(
    log_dir: str,
    config: GateConfig,
    days: int = 1,
    baseline_dir: str | None = None,
    baseline_days: int = 7,
    cases_file: str | None = None,
) -> CheckResult:
    """品質ゲート判定を実行する。"""
    current = load_records(log_dir, days=days)
    baseline = (
        load_records(baseline_dir or log_dir, days=baseline_days)
        if baseline_dir or baseline_days
        else []
    )

    if not current:
        return CheckResult(
            current_runs=0,
            baseline_runs=len(baseline),
            overall_rate=0.0,
            s1_rate=0.0,
            s1_passed=0,
            s1_total=0,
            thresholds=[
                ThresholdResult(
                    name="data_available",
                    threshold=1,
                    actual=0,
                    passed=False,
                    detail="No current run data found",
                )
            ],
        )

    # Pass rates
    total = len(current)
    passed = sum(1 for r in current if r.passed)
    overall_rate = (passed / total * 100) if total else 0.0

    s1 = [r for r in current if r.severity == "S1"]
    s1_passed = sum(1 for r in s1 if r.passed)
    s1_total = len(s1)
    s1_rate = (s1_passed / s1_total * 100) if s1_total else 100.0

    # Threshold checks
    checks: list[ThresholdResult] = []

    checks.append(
        ThresholdResult(
            name="S1 pass rate",
            threshold=config.s1_pass_rate,
            actual=s1_rate,
            passed=s1_rate >= config.s1_pass_rate,
            detail=f"{s1_passed}/{s1_total}",
        )
    )
    checks.append(
        ThresholdResult(
            name="Overall pass rate",
            threshold=config.overall_pass_rate,
            actual=overall_rate,
            passed=overall_rate >= config.overall_pass_rate,
            detail=f"{passed}/{total}",
        )
    )

    # Retrieval precision (optional)
    if config.retrieval_precision_threshold > 0:
        hits = sum(1 for r in current if r.retrieval_hit is True)
        ret_cases = sum(1 for r in current if r.retrieval_hit is not None)
        ret_prec = (hits / ret_cases * 100) if ret_cases else 0.0
        checks.append(
            ThresholdResult(
                name="Retrieval precision",
                threshold=config.retrieval_precision_threshold,
                actual=ret_prec,
                passed=ret_prec >= config.retrieval_precision_threshold,
                detail=f"{hits}/{ret_cases}",
            )
        )

    # Per-case min_pass_rate (from CSV)
    case_checks: list[ThresholdResult] = []
    if cases_file:
        from .loader import load_cases

        cases = load_cases(cases_file)
        case_rates = case_pass_rates(current)
        for c in cases:
            if c.min_pass_rate > 0:
                actual = case_rates.get(c.case_id, 0.0) * 100
                case_checks.append(
                    ThresholdResult(
                        name=f"case:{c.case_id}",
                        threshold=c.min_pass_rate,
                        actual=actual,
                        passed=actual >= c.min_pass_rate,
                        detail=c.name,
                    )
                )

    return CheckResult(
        current_runs=total,
        baseline_runs=len(baseline),
        overall_rate=overall_rate,
        s1_rate=s1_rate,
        s1_passed=s1_passed,
        s1_total=s1_total,
        thresholds=checks,
        case_thresholds=case_checks,
    )


# ------------------------------------------------------------------
# Markdown rendering
# ------------------------------------------------------------------


def render_gate_markdown(result: CheckResult) -> str:
    """ゲート結果を Markdown 形式で出力する。"""
    status = "✅ PASS" if result.gate_passed else "🔴 FAIL"
    lines = [f"## RAG Quality Gate: {status}\n"]

    lines.append("| Metric | Actual | Threshold | Status |")
    lines.append("|--------|--------|-----------|--------|")
    for t in result.thresholds:
        icon = "✅" if t.passed else "❌"
        lines.append(f"| {t.name} | {t.actual:.1f}% | {t.threshold:.1f}% | {icon} |")

    if result.case_thresholds:
        failed = [t for t in result.case_thresholds if not t.passed]
        if failed:
            lines.append("\n### Per-case Failures")
            lines.append("| Case | Actual | Threshold | Name |")
            lines.append("|------|--------|-----------|------|")
            for t in failed:
                lines.append(f"| {t.name} | {t.actual:.1f}% | {t.threshold:.1f}% | {t.detail} |")

    return "\n".join(lines) + "\n"
