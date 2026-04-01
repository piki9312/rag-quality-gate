"""Gate check — ベースライン比較 + 閾値判定 → pass/fail。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from rqg.domain import GateDecision, GateNextAction

from .aggregate import case_pass_rates, failure_category_breakdown, severity_pass_rate
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


def load_failure_actions_from_quality_pack(path: str | Path) -> dict[str, str]:
    """Load failure category -> next action hints from quality-pack.yml."""
    import yaml

    file_path = Path(path)
    if not file_path.exists():
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}

    patterns = data.get("common_failure_patterns", [])
    if not isinstance(patterns, list):
        return {}

    actions: dict[str, str] = {}
    for item in patterns:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue

        # Accept both legacy "action" and current "first_action" fields.
        action = item.get("first_action") or item.get("action")
        if not isinstance(action, str) or not action.strip():
            continue

        actions[name.strip()] = action.strip()
    return actions


DEFAULT_NEXT_ACTION_HINT = "Define next action in weekly review issue"


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
    run_id: str
    current_runs: int
    baseline_runs: int
    overall_rate: float
    s1_rate: float
    s1_passed: int
    s1_total: int
    thresholds: list[ThresholdResult] = field(default_factory=list)
    case_thresholds: list[ThresholdResult] = field(default_factory=list)
    failure_categories: dict[str, int] = field(default_factory=dict)

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
            run_id="check-no-data",
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
    latest_record = max(current, key=lambda r: r.timestamp)

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
        run_id=latest_record.run_id,
        current_runs=total,
        baseline_runs=len(baseline),
        overall_rate=overall_rate,
        s1_rate=s1_rate,
        s1_passed=s1_passed,
        s1_total=s1_total,
        thresholds=checks,
        case_thresholds=case_checks,
        failure_categories=failure_category_breakdown(current),
    )


def _build_structured_next_actions(
    failure_categories: dict[str, int],
    failure_actions: dict[str, str] | None = None,
) -> list[GateNextAction]:
    if not failure_categories:
        return []

    next_actions: list[GateNextAction] = []
    for category in sorted(failure_categories):
        count = failure_categories.get(category, 0)
        if count <= 0:
            continue

        action = DEFAULT_NEXT_ACTION_HINT
        if failure_actions and category in failure_actions:
            hinted = failure_actions[category].strip()
            if hinted:
                action = hinted

        next_actions.append(
            GateNextAction(
                failure_category=category,
                count=count,
                action=action,
            )
        )

    return next_actions


def build_gate_decision(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
) -> GateDecision:
    """Convert a gate check result into a GateDecision model."""
    failed_thresholds = [t for t in result.thresholds if not t.passed]
    failed_case_thresholds = [t for t in result.case_thresholds if not t.passed]

    reasons = [
        f"{t.name}: {t.actual:.1f} < {t.threshold:.1f} ({t.detail})".rstrip(" ()")
        for t in failed_thresholds
    ]
    reasons.extend(
        f"{t.name}: {t.actual:.1f} < {t.threshold:.1f} ({t.detail})".rstrip(" ()")
        for t in failed_case_thresholds
    )

    status = "pass" if result.gate_passed else "fail"
    metrics = {
        "overall_pass_rate": result.overall_rate,
        "s1_pass_rate": result.s1_rate,
        "current_runs": float(result.current_runs),
        "baseline_runs": float(result.baseline_runs),
    }
    next_actions = _build_structured_next_actions(result.failure_categories, failure_actions)

    return GateDecision(
        run_id=result.run_id,
        status=status,
        reasons=reasons,
        metrics=metrics,
        next_actions=next_actions,
        created_at=datetime.now(timezone.utc),
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

    if result.failure_categories:
        lines.append("\n### Failure Categories")
        lines.append("| Category | Count |")
        lines.append("|----------|-------|")
        for category, count in result.failure_categories.items():
            lines.append(f"| {category} | {count} |")

    return "\n".join(lines) + "\n"


def render_gate_markdown(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
) -> str:
    """Render a gate check result as Markdown."""
    status = "PASS" if result.gate_passed else "FAIL"
    lines = [f"## RAG Quality Gate: {status}\n"]

    lines.append("| Metric | Actual | Threshold | Status |")
    lines.append("|--------|--------|-----------|--------|")
    for t in result.thresholds:
        icon = "OK" if t.passed else "NG"
        lines.append(f"| {t.name} | {t.actual:.1f}% | {t.threshold:.1f}% | {icon} |")

    if result.case_thresholds:
        failed = [t for t in result.case_thresholds if not t.passed]
        if failed:
            lines.append("\n### Per-case Failures")
            lines.append("| Case | Actual | Threshold | Name |")
            lines.append("|------|--------|-----------|------|")
            for t in failed:
                lines.append(f"| {t.name} | {t.actual:.1f}% | {t.threshold:.1f}% | {t.detail} |")

    if result.failure_categories:
        lines.append("\n### Failure Categories")
        lines.append("| Category | Count |")
        lines.append("|----------|-------|")
        for category, count in result.failure_categories.items():
            lines.append(f"| {category} | {count} |")

    if result.failure_categories:
        lines.append("\n### Next Actions")
        lines.append("| Failure Category | Next Action | Owner | Due |")
        lines.append("|------------------|-------------|-------|-----|")
        for category in result.failure_categories:
            action = DEFAULT_NEXT_ACTION_HINT
            if failure_actions and category in failure_actions:
                action = failure_actions[category]
            safe_action = action.replace("|", "\\|")
            lines.append(f"| {category} | {safe_action} | T.B.D. | T.B.D. |")

    return "\n".join(lines) + "\n"
