"""Gate check — ベースライン比較 + 閾値判定 → pass/fail。"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from rqg.domain import GateDecision, GateNextAction, GatePackMetadata

from .artifact_exposure_policy import ArtifactType, FieldExposure, resolve_artifact_exposure
from .aggregate import case_pass_rates, failure_category_breakdown, failure_category_case_ids
from .models import QARunRecord, QATestCase
from .provenance import (
    SIMULATION_WARNING_EN,
    SIMULATION_WARNING_JA,
    append_simulation_warning,
    is_simulation_execution_mode,
    load_run_provenance,
)
from .reason_taxonomy import (
    REASON_EMBEDDING_FALLBACK_USED,
    REASON_JUDGE_FALLBACK_USED,
    REASON_JUDGE_UNRELIABLE,
    REASON_NEEDS_HUMAN_REVIEW,
    canonical_reason,
)
from .report_mode_policy import VALID_REPORT_MODES, normalize_report_mode_value
from .staleness import CaseStalenessItem, summarize_case_staleness

logger = logging.getLogger(__name__)

VALID_AGGREGATION_POLICIES = {"latest_run", "window"}
CI_SAFE_FAILURE_CODES = {
    "answer_mismatch",
    "bad_reference",
    "condition_mismatch",
    "deadline_or_period_mismatch",
    "embedding_reliability",
    "error",
    "exception_omission",
    "human_review",
    "insufficient_context",
    "judge_fallback",
    "judge_reliability",
    "keyword_miss",
    "missing_evidence",
    "negation_error",
    "numeric_mismatch",
    "over_assertive_answer",
    "policy_gap",
    "retrieval_miss",
    "source_mismatch",
    "stale",
    "synthesis",
    "tool_failure",
    "unknown",
    "unsupported_claim",
}


def normalize_aggregation_policy(value: object) -> str:
    """Normalize gate aggregation policy names."""
    if value is None:
        return "latest_run"

    normalized = str(value).strip().lower().replace("-", "_")
    if normalized == "":
        return "latest_run"
    if normalized in {"latest", "latest_run"}:
        return "latest_run"
    if normalized == "window":
        return "window"

    allowed = ", ".join(sorted(VALID_AGGREGATION_POLICIES))
    raise ValueError(f"Invalid aggregation_policy '{value}' (allowed: {allowed})")


def normalize_report_mode(value: object) -> str:
    """Normalize additive report mode names.

    Kept as a compatibility wrapper for existing imports. New command-level
    mode selection should use ReportModePolicy.
    """
    return normalize_report_mode_value(value)


def report_mode_exposes_sensitive_fields(report_mode: object) -> bool:
    return normalize_report_mode(report_mode) == "full"


# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------


@dataclass
class GateConfig:
    """品質ゲートの閾値設定。"""

    s1_pass_rate: float = 100.0
    overall_pass_rate: float = 80.0
    expected_evidence_hit_rate_threshold: float = 0.0  # 0 = check disabled
    min_faithfulness: float = 0.0  # 0 = チェックしない (例: 70.0 = 70%以上)
    min_evidence_recall: float = 0.0  # 0 = チェックしない (例: 90.0 = 90%以上)
    max_latency_p95_ms: float = 0.0  # 0 = チェックしない
    max_cost_per_query_usd: float = 0.0
    max_overall_drop_pct: float = 0.0
    max_s1_drop_pct: float = 0.0
    case_staleness_days: int = 0
    min_fresh_case_review_rate: float = 0.0

    # Warn thresholds (0 = disabled).  When a metric passes the fail threshold
    # but misses the warn threshold the gate status becomes "warn" instead of
    # "pass".  Warn does **not** block (exit 0 by default) but is surfaced in
    # reports and gate-decision.json so operators notice degradation early.
    s1_pass_rate_warn: float = 0.0
    overall_pass_rate_warn: float = 0.0
    fresh_case_review_rate_warn: float = 0.0
    judge_relevance_warn: float = 0.0  # 0 = 警告しない
    aggregation_policy: str = "latest_run"  # latest_run | window

    @property
    def staleness_policy_enabled(self) -> bool:
        return (
            self.case_staleness_days > 0
            or self.min_fresh_case_review_rate > 0
            or self.fresh_case_review_rate_warn > 0
        )

    @classmethod
    def from_yaml(cls, path: str) -> GateConfig:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        th = data.get("thresholds", {})
        return cls(
            s1_pass_rate=th.get("s1_pass_rate", 100.0),
            overall_pass_rate=th.get("overall_pass_rate", 80.0),
            expected_evidence_hit_rate_threshold=th.get(
                "expected_evidence_hit_rate",
                th.get("retrieval_precision", 0.0),
            ),
            min_faithfulness=th.get("min_faithfulness", 0.0),
            min_evidence_recall=th.get("min_evidence_recall", 0.0),
            max_latency_p95_ms=th.get("max_latency_p95_ms", 0.0),
            max_cost_per_query_usd=th.get("max_cost_per_query_usd", 0.0),
            max_overall_drop_pct=th.get("max_overall_drop_pct", 0.0),
            max_s1_drop_pct=th.get("max_s1_drop_pct", 0.0),
            case_staleness_days=int(th.get("case_staleness_days", 0) or 0),
            min_fresh_case_review_rate=th.get("min_fresh_case_review_rate", 0.0),
            s1_pass_rate_warn=th.get("s1_pass_rate_warn", 0.0),
            overall_pass_rate_warn=th.get("overall_pass_rate_warn", 0.0),
            fresh_case_review_rate_warn=th.get("fresh_case_review_rate_warn", 0.0),
            judge_relevance_warn=th.get("judge_relevance_warn", 0.0),
            aggregation_policy=normalize_aggregation_policy(th.get("aggregation_policy")),
        )


def load_quality_pack_payload(path: str | Path) -> dict[str, Any]:
    """Load quality-pack.yml as a mapping, returning {} on error."""
    import yaml

    file_path = Path(path)
    if not file_path.exists():
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("failed to load quality-pack %s: %s", file_path, exc)
        return {}

    if not isinstance(data, dict):
        return {}
    return data


def load_failure_actions_from_quality_pack(path: str | Path) -> dict[str, str]:
    """Load failure category -> next action hints from quality-pack.yml."""
    data = load_quality_pack_payload(path)
    if not data:
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


def load_review_steward_from_quality_pack(path: str | Path) -> str | None:
    """Load the fixed weekly review steward from quality-pack.yml."""
    data = load_quality_pack_payload(path)
    if not data:
        return None

    pack_meta = data.get("pack", {})
    if not isinstance(pack_meta, dict):
        return None

    review_steward = str(pack_meta.get("review_steward", "")).strip()
    return review_steward or None


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
    warn_threshold: float = 0.0
    warned: bool = False


@dataclass
class CheckResult:
    run_id: str
    current_runs: int
    baseline_runs: int
    overall_rate: float
    s1_rate: float
    s1_passed: int
    s1_total: int
    aggregation_policy: str = "latest_run"
    baseline_overall_rate: float | None = None
    baseline_s1_rate: float | None = None
    overall_drop: float | None = None
    s1_drop: float | None = None
    thresholds: list[ThresholdResult] = field(default_factory=list)
    case_thresholds: list[ThresholdResult] = field(default_factory=list)
    failure_categories: dict[str, int] = field(default_factory=dict)
    failure_case_ids: dict[str, list[str]] = field(default_factory=dict)
    avg_faithfulness: float | None = None
    faithfulness_scored: int = 0
    avg_judge_relevance: float | None = None
    judge_relevance_scored: int = 0
    avg_evidence_recall: float | None = None
    evidence_recall_scored: int = 0
    stale_after_days: int = 0
    fresh_case_review_rate: float | None = None
    fresh_case_count: int = 0
    fresh_case_total: int = 0
    stale_cases: list[CaseStalenessItem] = field(default_factory=list)
    judge_fallback_count: int = 0
    judge_failure_types: dict[str, int] = field(default_factory=dict)
    judge_reliability: str = "high"
    embedding_fallback_count: int = 0
    embedding_fallback_used: bool = False
    embedding_fallback_reason: str | None = None
    retrieval_reliability: str = "high"
    needs_human_review: bool = False
    current_records: list[QARunRecord] = field(default_factory=list)
    active_cases: list[QATestCase] = field(default_factory=list)
    execution_mode: str = "real"
    run_provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def gate_passed(self) -> bool:
        return all(t.passed for t in self.thresholds) and all(
            t.passed for t in self.case_thresholds
        )

    @property
    def gate_status(self) -> str:
        """Return 'pass', 'warn', or 'fail'."""
        if not self.gate_passed:
            return "fail"
        if any(t.warned for t in self.thresholds) or any(t.warned for t in self.case_thresholds):
            return "warn"
        return "pass"


# ------------------------------------------------------------------
# JSONL I/O
# ------------------------------------------------------------------


def load_records(
    log_dir: str,
    days: int | None = None,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[QARunRecord]:
    """JSONL ファイルから QARunRecord を読み込む。"""
    path = Path(log_dir)
    if not path.exists():
        return []

    cutoff = since
    if cutoff is None and days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    records: list[QARunRecord] = []
    for f in sorted(path.glob("*.jsonl")):
        # Eval logs are date-based (YYYYMMDD.jsonl). Ignore other JSONL artifacts.
        if len(f.stem) != 8 or not f.stem.isdigit():
            continue
        with open(f, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = QARunRecord.model_validate_json(line)
                    if cutoff and rec.timestamp < cutoff:
                        continue
                    if until and rec.timestamp >= until:
                        continue
                    records.append(rec)
                except (ValueError, ValidationError) as exc:
                    logger.debug("skipping malformed JSONL line in %s: %s", f.name, exc)
                    continue
    return records


def _average_metric(records: list[QARunRecord], field_name: str) -> tuple[float | None, int]:
    values = [
        value for record in records if (value := getattr(record, field_name, None)) is not None
    ]
    if not values:
        return None, 0
    return sum(values) / len(values) * 100, len(values)


def _count_string_field(records: list[QARunRecord], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(getattr(record, field_name, "") or "").strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _judge_reliability_label(
    *,
    total_runs: int,
    judge_scored_runs: int,
    judge_fallback_count: int,
) -> str:
    if total_runs <= 0:
        return "low"
    if judge_fallback_count > 0 or judge_scored_runs < total_runs:
        return "low"
    return "high"


def _group_records_by_run(records: list[QARunRecord]) -> dict[str, list[QARunRecord]]:
    grouped: dict[str, list[QARunRecord]] = {}
    for record in records:
        grouped.setdefault(record.run_id, []).append(record)
    return grouped


def _select_records_by_policy(
    records: list[QARunRecord],
    aggregation_policy: str,
) -> list[QARunRecord]:
    if aggregation_policy == "window" or not records:
        return records

    grouped = _group_records_by_run(records)
    latest_run_id, latest_records = max(
        grouped.items(),
        key=lambda item: (max(record.timestamp for record in item[1]), item[0]),
    )
    logger.debug(
        "selected latest run for gate aggregation: %s (%d records)",
        latest_run_id,
        len(latest_records),
    )
    return latest_records


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
    now = datetime.now(timezone.utc)
    current_cutoff = now - timedelta(days=days) if days else None
    current = load_records(log_dir, since=current_cutoff)

    baseline: list[QARunRecord] = []
    same_log_source = not baseline_dir or Path(baseline_dir).resolve() == Path(log_dir).resolve()
    if baseline_dir or baseline_days:
        if same_log_source:
            baseline_until = current_cutoff
            baseline_since = (
                baseline_until - timedelta(days=baseline_days)
                if baseline_until and baseline_days
                else None
            )
            baseline = load_records(log_dir, since=baseline_since, until=baseline_until)
        else:
            baseline_since = now - timedelta(days=baseline_days) if baseline_days else None
            baseline = load_records(baseline_dir or log_dir, since=baseline_since)

    active_cases = None
    staleness_summary = None
    if cases_file:
        from .loader import filter_cases_by_status, load_cases

        loaded_cases = load_cases(cases_file)
        active_cases = filter_cases_by_status(loaded_cases, allowed_statuses={"active"})
        if config.case_staleness_days > 0:
            staleness_summary = summarize_case_staleness(
                active_cases,
                stale_after_days=config.case_staleness_days,
                now=now,
            )
        active_case_ids = {case.case_id for case in active_cases}
        current = [record for record in current if record.case_id in active_case_ids]
        baseline = [record for record in baseline if record.case_id in active_case_ids]

    aggregation_policy = normalize_aggregation_policy(config.aggregation_policy)
    current = _select_records_by_policy(current, aggregation_policy)
    baseline = _select_records_by_policy(baseline, aggregation_policy)

    baseline_overall_rate: float | None = None
    baseline_s1_rate: float | None = None
    if baseline:
        baseline_total = len(baseline)
        baseline_passed = sum(1 for r in baseline if r.passed)
        baseline_overall_rate = (baseline_passed / baseline_total * 100) if baseline_total else None

        baseline_s1 = [r for r in baseline if r.severity == "S1"]
        baseline_s1_total = len(baseline_s1)
        if baseline_s1_total:
            baseline_s1_passed = sum(1 for r in baseline_s1 if r.passed)
            baseline_s1_rate = baseline_s1_passed / baseline_s1_total * 100

    if not current:
        return CheckResult(
            run_id="check-no-data",
            aggregation_policy=aggregation_policy,
            current_runs=0,
            baseline_runs=len(baseline),
            overall_rate=0.0,
            s1_rate=0.0,
            s1_passed=0,
            s1_total=0,
            baseline_overall_rate=baseline_overall_rate,
            baseline_s1_rate=baseline_s1_rate,
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
    execution_modes = {
        str(record.execution_mode or "").strip().lower()
        for record in current
        if str(record.execution_mode or "").strip()
    }
    execution_mode = (
        sorted(execution_modes)[0] if len(execution_modes) == 1 else "mixed_execution_modes"
    )
    run_provenance = load_run_provenance(log_dir, latest_record.run_id)

    s1 = [r for r in current if r.severity == "S1"]
    s1_passed = sum(1 for r in s1 if r.passed)
    s1_total = len(s1)
    s1_rate = (s1_passed / s1_total * 100) if s1_total else 100.0
    avg_faithfulness, faithfulness_scored = _average_metric(current, "faithfulness_score")
    avg_judge_relevance, judge_relevance_scored = _average_metric(current, "judge_relevance")
    avg_evidence_recall, evidence_recall_scored = _average_metric(current, "evidence_recall")
    judge_fallback_count = sum(1 for record in current if record.judge_fallback_used)
    judge_failure_types = _count_string_field(current, "judge_failure_type")
    embedding_fallback_count = sum(1 for record in current if record.embedding_fallback_used)
    embedding_fallback_reasons = _count_string_field(current, "embedding_fallback_reason")
    embedding_fallback_reason = next(iter(embedding_fallback_reasons), None)
    judge_reliability = _judge_reliability_label(
        total_runs=total,
        judge_scored_runs=judge_relevance_scored,
        judge_fallback_count=judge_fallback_count,
    )
    retrieval_empty_s1 = any(
        record.severity == "S1" and record.retrieved_ids == [] for record in current
    )
    retrieval_reliability = "low" if retrieval_empty_s1 else "high"
    needs_human_review = (
        judge_fallback_count > 0
        or embedding_fallback_count > 0
        or judge_relevance_scored < total
        or retrieval_empty_s1
    )

    # Threshold checks
    checks: list[ThresholdResult] = []
    overall_drop: float | None = None
    s1_drop: float | None = None

    def _should_warn(actual: float, fail_th: float, warn_th: float) -> bool:
        return warn_th > 0 and actual >= fail_th and actual < warn_th

    checks.append(
        ThresholdResult(
            name="S1 pass rate",
            threshold=config.s1_pass_rate,
            actual=s1_rate,
            passed=s1_rate >= config.s1_pass_rate,
            detail=f"{s1_passed}/{s1_total}",
            warn_threshold=config.s1_pass_rate_warn,
            warned=_should_warn(s1_rate, config.s1_pass_rate, config.s1_pass_rate_warn),
        )
    )
    checks.append(
        ThresholdResult(
            name="Overall pass rate",
            threshold=config.overall_pass_rate,
            actual=overall_rate,
            passed=overall_rate >= config.overall_pass_rate,
            detail=f"{passed}/{total}",
            warn_threshold=config.overall_pass_rate_warn,
            warned=_should_warn(
                overall_rate, config.overall_pass_rate, config.overall_pass_rate_warn
            ),
        )
    )

    # Expected evidence hit rate (optional)
    if config.expected_evidence_hit_rate_threshold > 0:
        hits = sum(1 for r in current if r.retrieval_hit is True)
        ret_cases = sum(1 for r in current if r.retrieval_hit is not None)
        hit_rate = (hits / ret_cases * 100) if ret_cases else 0.0
        checks.append(
            ThresholdResult(
                name="Expected evidence hit rate",
                threshold=config.expected_evidence_hit_rate_threshold,
                actual=hit_rate,
                passed=hit_rate >= config.expected_evidence_hit_rate_threshold,
                detail=f"{hits}/{ret_cases}",
            )
        )

    # Faithfulness (optional)
    if config.min_faithfulness > 0:
        avg_faith = avg_faithfulness if avg_faithfulness is not None else 0.0
        checks.append(
            ThresholdResult(
                name="Avg faithfulness",
                threshold=config.min_faithfulness,
                actual=avg_faith,
                passed=avg_faith >= config.min_faithfulness,
                detail=f"{faithfulness_scored} scored",
            )
        )

    # Evidence recall (optional)
    if config.min_evidence_recall > 0:
        avg_recall = avg_evidence_recall if avg_evidence_recall is not None else 0.0
        checks.append(
            ThresholdResult(
                name="Avg expected evidence recall",
                threshold=config.min_evidence_recall,
                actual=avg_recall,
                passed=avg_recall >= config.min_evidence_recall,
                detail=f"{evidence_recall_scored} scored",
            )
        )

    # Judge relevance (warn only)
    if config.judge_relevance_warn > 0:
        avg_relevance = avg_judge_relevance if avg_judge_relevance is not None else 0.0
        checks.append(
            ThresholdResult(
                name="Avg judge relevance",
                threshold=config.judge_relevance_warn,
                actual=avg_relevance,
                passed=True,
                detail=f"{judge_relevance_scored} scored",
                warn_threshold=config.judge_relevance_warn,
                warned=avg_relevance < config.judge_relevance_warn,
            )
        )

    # Regression checks (optional)
    if config.max_overall_drop_pct > 0:
        if baseline_overall_rate is None:
            checks.append(
                ThresholdResult(
                    name="Overall pass rate drop",
                    threshold=config.max_overall_drop_pct,
                    actual=0.0,
                    passed=False,
                    detail="No baseline run data found",
                )
            )
        else:
            overall_drop = max(0.0, baseline_overall_rate - overall_rate)
            checks.append(
                ThresholdResult(
                    name="Overall pass rate drop",
                    threshold=config.max_overall_drop_pct,
                    actual=overall_drop,
                    passed=overall_drop <= config.max_overall_drop_pct,
                    detail=f"baseline={baseline_overall_rate:.1f}% current={overall_rate:.1f}%",
                )
            )

    if config.max_s1_drop_pct > 0:
        if baseline_s1_rate is None:
            checks.append(
                ThresholdResult(
                    name="S1 pass rate drop",
                    threshold=config.max_s1_drop_pct,
                    actual=0.0,
                    passed=False,
                    detail="No baseline S1 run data found",
                )
            )
        else:
            s1_drop = max(0.0, baseline_s1_rate - s1_rate)
            checks.append(
                ThresholdResult(
                    name="S1 pass rate drop",
                    threshold=config.max_s1_drop_pct,
                    actual=s1_drop,
                    passed=s1_drop <= config.max_s1_drop_pct,
                    detail=f"baseline={baseline_s1_rate:.1f}% current={s1_rate:.1f}%",
                )
            )

    if staleness_summary is not None:
        freshness_threshold = config.min_fresh_case_review_rate
        freshness_warn_threshold = config.fresh_case_review_rate_warn
        freshness_actual = staleness_summary.fresh_rate
        freshness_passed = True
        freshness_warned = False
        if freshness_threshold > 0:
            freshness_passed = freshness_actual >= freshness_threshold
            freshness_warned = _should_warn(
                freshness_actual,
                freshness_threshold,
                freshness_warn_threshold,
            )
        elif freshness_warn_threshold > 0:
            freshness_warned = freshness_actual < freshness_warn_threshold

        if freshness_threshold > 0 or freshness_warn_threshold > 0:
            checks.append(
                ThresholdResult(
                    name="Fresh case review rate",
                    threshold=freshness_threshold or freshness_warn_threshold,
                    actual=freshness_actual,
                    passed=freshness_passed,
                    detail=(
                        f"{staleness_summary.fresh_cases}/{staleness_summary.total_cases} "
                        f"fresh within {staleness_summary.stale_after_days} days"
                    ),
                    warn_threshold=freshness_warn_threshold,
                    warned=freshness_warned,
                )
            )

    # Per-case min_pass_rate (from CSV)
    case_checks: list[ThresholdResult] = []
    if active_cases is not None:
        case_rates = case_pass_rates(current)
        for c in active_cases:
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
        aggregation_policy=aggregation_policy,
        current_runs=total,
        baseline_runs=len(baseline),
        overall_rate=overall_rate,
        s1_rate=s1_rate,
        s1_passed=s1_passed,
        s1_total=s1_total,
        baseline_overall_rate=baseline_overall_rate,
        baseline_s1_rate=baseline_s1_rate,
        overall_drop=overall_drop,
        s1_drop=s1_drop,
        thresholds=checks,
        case_thresholds=case_checks,
        failure_categories=failure_category_breakdown(current),
        failure_case_ids=failure_category_case_ids(current),
        avg_faithfulness=avg_faithfulness,
        faithfulness_scored=faithfulness_scored,
        avg_judge_relevance=avg_judge_relevance,
        judge_relevance_scored=judge_relevance_scored,
        avg_evidence_recall=avg_evidence_recall,
        evidence_recall_scored=evidence_recall_scored,
        stale_after_days=staleness_summary.stale_after_days if staleness_summary else 0,
        fresh_case_review_rate=staleness_summary.fresh_rate if staleness_summary else None,
        fresh_case_count=staleness_summary.fresh_cases if staleness_summary else 0,
        fresh_case_total=staleness_summary.total_cases if staleness_summary else 0,
        stale_cases=staleness_summary.stale_cases if staleness_summary else [],
        judge_fallback_count=judge_fallback_count,
        judge_failure_types=judge_failure_types,
        judge_reliability=judge_reliability,
        embedding_fallback_count=embedding_fallback_count,
        embedding_fallback_used=embedding_fallback_count > 0,
        embedding_fallback_reason=embedding_fallback_reason,
        retrieval_reliability=retrieval_reliability,
        needs_human_review=needs_human_review,
        current_records=current,
        active_cases=active_cases or [],
        execution_mode=execution_mode or "needs_review",
        run_provenance=run_provenance,
    )


def _build_structured_next_actions(
    failure_categories: dict[str, int],
    failure_actions: dict[str, str] | None = None,
    failure_case_ids: dict[str, list[str]] | None = None,
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

        case_ids = (failure_case_ids or {}).get(category, [])

        next_actions.append(
            GateNextAction(
                failure_category=category,
                count=count,
                action=action,
                affected_case_ids=case_ids,
            )
        )

    return next_actions


def _format_threshold_reason(threshold: ThresholdResult) -> str:
    reason = f"{threshold.name}: {threshold.actual:.1f} < {threshold.threshold:.1f}"
    detail = threshold.detail.strip()
    if detail:
        return f"{reason} ({detail})"
    return reason


def _executive_promotion_summary(status: str) -> str:
    if status == "PASS":
        return "Recommended. This pack meets the configured gate thresholds."
    if status == "FAIL":
        return "Not recommended. This pack should not be promoted to production."
    return "Review required. This pack met hard thresholds but triggered warning conditions."


def _main_failure_category_summary(failure_categories: dict[str, int]) -> str:
    if not failure_categories:
        return "None"

    category, count = sorted(
        failure_categories.items(),
        key=lambda item: (-item[1], item[0]),
    )[0]
    case_label = "case" if count == 1 else "cases"
    return f"{category} ({count} {case_label})"


def map_overall_decision(result: CheckResult) -> str:
    """Map gate status into a customer-facing overall decision."""
    policy_status = _policy_status_for_result(result)
    if policy_status == "block":
        return "ng"
    if policy_status in {"warn", "needs_human_review"} or result.needs_human_review:
        return "needs_confirmation"
    if result.gate_status == "fail":
        return "needs_confirmation"
    return "ok"


def collect_target_docs(result: CheckResult) -> list[str]:
    docs: list[str] = []
    seen: set[str] = set()
    for case in result.active_cases:
        source_doc = str(case.source_doc or "").strip()
        if not source_doc or source_doc in seen:
            continue
        seen.add(source_doc)
        docs.append(source_doc)
    return docs


def collect_target_docs_if_report_mode_allows(
    result: CheckResult, report_mode: object
) -> list[str]:
    policy = resolve_artifact_exposure(ArtifactType.GATE_REPORT_JSON, report_mode)
    exposure = policy.exposure_for("target_docs")
    target_docs = collect_target_docs(result)
    if exposure == FieldExposure.ALLOWED:
        return target_docs
    if exposure == FieldExposure.HASHED_ONLY:
        return [_stable_text_hash(value) for value in target_docs]
    return []


def build_customer_report_summary(result: CheckResult) -> dict[str, object]:
    total_cases = len(result.current_records) if result.current_records else result.current_runs
    if result.current_records:
        passed_cases = sum(1 for record in result.current_records if record.passed)
    else:
        passed_cases = int(round(total_cases * result.overall_rate / 100)) if total_cases else 0
    failed_cases = max(0, total_cases - passed_cases)
    s1_failed_cases = max(0, result.s1_total - result.s1_passed)
    overall_decision = map_overall_decision(result)

    if is_simulation_execution_mode(result.execution_mode):
        headline = "要確認。mock / simulation 実行のため、実システム品質の証跡には使えません。"
    elif overall_decision == "ng":
        headline = "NG。重大な失敗または block 判定があるため、本番反映は推奨されません。"
    elif overall_decision == "needs_confirmation":
        headline = "要確認。警告条件または信頼性低下があるため、人手確認後に判断してください。"
    else:
        headline = "OK。現在の閾値では本番反映可能です。"

    return {
        "headline": headline,
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "s1_failed_cases": s1_failed_cases,
        "overall_pass_rate": result.overall_rate,
        "s1_pass_rate": result.s1_rate,
        "main_failure_category": _main_failure_category_summary(result.failure_categories),
        "needs_human_review": result.needs_human_review,
        "judge_fallback_count": result.judge_fallback_count,
    }


def build_case_report_rows(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
    *,
    report_mode: str = "full",
    artifact_type: ArtifactType | str = ArtifactType.GATE_REPORT_JSON,
) -> list[dict[str, object]]:
    case_by_id = {case.case_id: case for case in result.active_cases}
    rows: list[dict[str, object]] = []
    policy = resolve_artifact_exposure(artifact_type, report_mode)

    for record in sorted(result.current_records, key=_case_report_sort_key):
        case = case_by_id.get(record.case_id)
        needs_human_review = _case_needs_human_review(record)
        raw_fields: dict[str, object] = {
            "case_id": record.case_id,
            "name": case.name if case else record.case_id,
            "severity": case.severity if case else record.severity,
            "category": case.category if case else record.category,
            "risk_domain": (
                case.risk_domain if case and case.risk_domain else record.risk_domain or ""
            ),
            "decision": _case_decision(record, needs_human_review),
            "pass_fail": "pass" if record.passed else "fail",
            "fail_reason": _case_fail_reason(record),
            "safe_reason": _safe_case_fail_reason(record),
            "failure_type_code": _safe_case_code(
                record.failure_category or record.failure_type or ""
            ),
            "next_actions": _case_next_actions(
                record,
                failure_actions=failure_actions,
                needs_human_review=needs_human_review,
            ),
            "judge_fallback_used": bool(record.judge_fallback_used),
            "judge_fallback_reason": record.judge_fallback_reason,
            "judge_reliability": result.judge_reliability,
            "needs_human_review": needs_human_review,
            "answer_hash": record.answer_hash or _stable_text_hash(record.answer),
            "question": case.question if case else "",
            "ai_answer": record.answer,
            "expected_answer": case.expected_answer if case else "",
            "expected_evidence": list(case.expected_evidence) if case else [],
            "retrieved_evidence": list(record.retrieved_ids),
            "source_doc": case.source_doc if case else "",
        }
        row: dict[str, object] = {}
        for field_name, value in raw_fields.items():
            exposure = policy.exposure_for(field_name)
            if exposure == FieldExposure.ALLOWED:
                row[field_name] = value
            elif exposure == FieldExposure.HASHED_ONLY:
                hashed_value = _stable_text_hash(value)
                row[f"{field_name}_hash"] = hashed_value
                if field_name == "case_id":
                    row[field_name] = f"case:{hashed_value}"
        rows.append(row)

    return rows


def build_ci_case_report_rows(result: CheckResult) -> list[dict[str, object]]:
    """Build CI-safe per-case rows without customer-authored identifiers or text."""
    rows: list[dict[str, object]] = []
    policy = resolve_artifact_exposure(ArtifactType.CI_CASE_ROW, "ci")
    for record in sorted(result.current_records, key=_case_report_sort_key):
        needs_human_review = _case_needs_human_review(record)
        raw_fields: dict[str, object] = {
            "case_id": record.case_id,
            "severity": record.severity,
            "decision": _case_decision(record, needs_human_review),
            "pass_fail": "pass" if record.passed else "fail",
            "failure_type_code": _safe_case_code(
                record.failure_category or record.failure_type or ""
            ),
            "needs_human_review": needs_human_review,
            "judge_fallback_used": bool(record.judge_fallback_used),
        }
        for key in (
            "latency_ms",
            "cost_usd",
            "evidence_recall",
            "faithfulness_score",
            "judge_relevance",
        ):
            value = getattr(record, key, None)
            if value is not None:
                raw_fields[key] = value
        row: dict[str, object] = {}
        for field_name, value in raw_fields.items():
            exposure = policy.exposure_for(field_name)
            if exposure == FieldExposure.ALLOWED:
                row[field_name] = value
            elif exposure == FieldExposure.HASHED_ONLY:
                row[f"{field_name}_hash"] = _stable_text_hash(value)
        rows.append(row)
    return rows


def _stable_case_id_hash(case_id: object) -> str:
    return _stable_text_hash(case_id)


def _stable_text_hash(value: object) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _safe_case_code(value: object) -> str:
    code = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if code in CI_SAFE_FAILURE_CODES:
        return code[:80]
    return "unknown"


def _case_report_sort_key(record: QARunRecord) -> tuple[int, int, int, str]:
    severity = str(record.severity or "").strip().upper()
    critical_fail_rank = 0 if severity == "S1" and not record.passed else 1
    fail_rank = 0 if not record.passed else 1
    severity_rank = 0 if severity == "S1" else 1
    return (critical_fail_rank, fail_rank, severity_rank, record.case_id)


def _case_needs_human_review(record: QARunRecord) -> bool:
    severity = str(record.severity or "").strip().upper()
    return bool(
        record.judge_fallback_used
        or record.embedding_fallback_used
        or (severity == "S1" and not record.passed)
    )


def _case_decision(record: QARunRecord, needs_human_review: bool) -> str:
    if not record.passed:
        return "ng"
    if needs_human_review:
        return "needs_confirmation"
    return "ok"


def _case_fail_reason(record: QARunRecord) -> str:
    reasons = [str(reason).strip() for reason in record.reasons if str(reason).strip()]
    if reasons:
        return "; ".join(reasons)
    if record.failure_category:
        return str(record.failure_category)
    if record.failure_type:
        return str(record.failure_type)
    if record.passed:
        return ""
    return "Gate check failed"


def _safe_case_fail_reason(record: QARunRecord) -> str:
    if record.failure_category:
        return str(record.failure_category)
    if record.failure_type:
        return str(record.failure_type)
    if record.passed:
        return ""
    return "Gate check failed"


def _case_next_actions(
    record: QARunRecord,
    *,
    failure_actions: dict[str, str] | None,
    needs_human_review: bool,
) -> list[str]:
    actions: list[str] = []
    failure_category = str(record.failure_category or "").strip()
    required_action = str(record.required_action or "").strip()

    if not record.passed:
        if failure_category:
            actions.append((failure_actions or {}).get(failure_category, DEFAULT_NEXT_ACTION_HINT))
        if required_action:
            actions.append(required_action)
    if record.judge_fallback_used:
        actions.append("Re-run judge-enabled evaluation and confirm model/API connectivity")
    if record.embedding_fallback_used:
        actions.append("Check embedding dependency/model loading and rebuild the retrieval index")
    if needs_human_review:
        actions.append("Route this case for manual review before approving the update")

    deduped: list[str] = []
    seen: set[str] = set()
    for action in actions:
        normalized = action.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _overall_decision_label(overall_decision: str) -> str:
    if overall_decision == "ng":
        return "NG"
    if overall_decision == "needs_confirmation":
        return "要確認"
    return "OK"


def _customer_action_label(action: object) -> str:
    text = str(action).strip()
    labels = {
        DEFAULT_NEXT_ACTION_HINT: "失敗ケースの原因を確認し、週次レビューで対応方針を決める",
        "block": "本番反映を止め、該当FAQ・規約・回答ロジックを修正する",
        "allow_with_warning": "注意付きで扱い、必要に応じてサポート担当者の確認を入れる",
        "needs_human_review": "人手確認に回し、承認後に本番反映を判断する",
        "Check embedding dependency/model loading and rebuild the retrieval index": (
            "検索モデルまたは依存関係を確認し、必要に応じて検索インデックスを再作成する"
        ),
        "Route this case for manual review before approving the update": (
            "このケースは人手で確認してから更新を承認する"
        ),
        "Route this run for manual review before approving the update": (
            "この実行結果は人手で確認してから更新を承認する"
        ),
    }
    return labels.get(text, text)


def build_gate_decision(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
    pack_metadata: dict[str, Any] | None = None,
    manual_review_summary: dict[str, object] | None = None,
) -> GateDecision:
    """Convert a gate check result into a GateDecision model."""
    failed_thresholds = [t for t in result.thresholds if not t.passed]
    failed_case_thresholds = [t for t in result.case_thresholds if not t.passed]

    reasons = [_format_threshold_reason(t) for t in failed_thresholds]
    reasons.extend(_format_threshold_reason(t) for t in failed_case_thresholds)

    status = result.gate_status

    # Append warn reasons when gate is not failing
    if status == "warn":
        warned_thresholds = [t for t in result.thresholds if t.warned]
        warned_case_thresholds = [t for t in result.case_thresholds if t.warned]
        for t in warned_thresholds:
            reasons.append(f"WARN {t.name}: {t.actual:.1f} < warn threshold {t.warn_threshold:.1f}")
        for t in warned_case_thresholds:
            reasons.append(f"WARN {t.name}: {t.actual:.1f} < warn threshold {t.warn_threshold:.1f}")

    if result.judge_fallback_count > 0:
        reasons.append(
            "Judge fallback detected; re-run evaluation and verify judge/API connectivity before release"
        )
    if result.embedding_fallback_used:
        reasons.append(
            "Embedding fallback detected; confirm embedding dependency/model health and rebuild the index"
        )
    if result.needs_human_review:
        reasons.append("Human review required because run reliability signals were degraded")
    if is_simulation_execution_mode(result.execution_mode):
        reasons.append(SIMULATION_WARNING_EN)
        reasons.append(SIMULATION_WARNING_JA)
    reason_codes = [canonical_reason(category) for category in result.failure_categories]
    if result.judge_fallback_count > 0:
        reason_codes.append(REASON_JUDGE_FALLBACK_USED)
    if result.judge_reliability == "low":
        reason_codes.append(REASON_JUDGE_UNRELIABLE)
    if result.embedding_fallback_used:
        reason_codes.append(REASON_EMBEDDING_FALLBACK_USED)
    if result.needs_human_review:
        reason_codes.append(REASON_NEEDS_HUMAN_REVIEW)
    reason_codes = list(dict.fromkeys(reason_codes))

    metrics = {
        "overall_pass_rate": result.overall_rate,
        "s1_pass_rate": result.s1_rate,
        "s1_fail_count": float(max(0, result.s1_total - result.s1_passed)),
        "current_runs": float(result.current_runs),
        "baseline_runs": float(result.baseline_runs),
        "judge_fallback_count": float(result.judge_fallback_count),
        "embedding_fallback_count": float(result.embedding_fallback_count),
    }
    if result.avg_faithfulness is not None:
        metrics["avg_faithfulness"] = result.avg_faithfulness
    metrics["faithfulness_scored_runs"] = float(result.faithfulness_scored)
    if result.avg_judge_relevance is not None:
        metrics["avg_judge_relevance"] = result.avg_judge_relevance
    metrics["judge_relevance_scored_runs"] = float(result.judge_relevance_scored)
    if result.avg_evidence_recall is not None:
        metrics["avg_evidence_recall"] = result.avg_evidence_recall
        metrics["avg_expected_evidence_recall"] = result.avg_evidence_recall
    metrics["evidence_recall_scored_runs"] = float(result.evidence_recall_scored)
    metrics["expected_evidence_recall_scored_runs"] = float(result.evidence_recall_scored)
    if result.baseline_overall_rate is not None:
        metrics["baseline_overall_pass_rate"] = result.baseline_overall_rate
    if result.baseline_s1_rate is not None:
        metrics["baseline_s1_pass_rate"] = result.baseline_s1_rate
    if result.overall_drop is not None:
        metrics["overall_pass_rate_drop"] = result.overall_drop
    if result.s1_drop is not None:
        metrics["s1_pass_rate_drop"] = result.s1_drop
    if result.fresh_case_review_rate is not None:
        metrics["fresh_case_review_rate"] = result.fresh_case_review_rate
        metrics["stale_case_count"] = float(len(result.stale_cases))
    fallback_summary: dict[str, object] = {
        "judge_fallback_used": result.judge_fallback_count > 0,
        "judge_fallback_count": result.judge_fallback_count,
        "judge_failure_types": result.judge_failure_types,
        "embedding_fallback_used": result.embedding_fallback_used,
        "embedding_fallback_count": result.embedding_fallback_count,
        "embedding_fallback_reason": result.embedding_fallback_reason,
        "retrieval_reliability": result.retrieval_reliability,
    }
    if is_simulation_execution_mode(result.execution_mode):
        fallback_summary["simulation_warning"] = {
            "en": SIMULATION_WARNING_EN,
            "ja": SIMULATION_WARNING_JA,
        }
    next_actions = _build_structured_next_actions(
        result.failure_categories, failure_actions, result.failure_case_ids
    )
    if result.judge_fallback_count > 0:
        next_actions.append(
            GateNextAction(
                failure_category="judge_reliability",
                count=result.judge_fallback_count,
                action="Re-run judge-enabled evaluation and confirm model/API connectivity",
            )
        )
    if result.embedding_fallback_used:
        next_actions.append(
            GateNextAction(
                failure_category="embedding_reliability",
                count=max(1, result.embedding_fallback_count),
                action="Check embedding dependency/model loading and rebuild the retrieval index",
            )
        )
    if result.needs_human_review:
        next_actions.append(
            GateNextAction(
                failure_category="human_review",
                count=1,
                action="Route this run for manual review before approving the update",
            )
        )
    policy_status = _policy_status_for_result(result)

    return GateDecision(
        run_id=result.run_id,
        status=status,
        policy_status=policy_status,
        reasons=reasons,
        reason_codes=reason_codes,
        metrics=metrics,
        execution_mode=result.execution_mode,
        provenance=result.run_provenance,
        next_actions=next_actions,
        judge_fallback_used=result.judge_fallback_count > 0,
        judge_fallback_count=result.judge_fallback_count,
        judge_failure_types=result.judge_failure_types,
        judge_reliability=result.judge_reliability,
        embedding_fallback_used=result.embedding_fallback_used,
        embedding_fallback_count=result.embedding_fallback_count,
        embedding_fallback_reason=result.embedding_fallback_reason,
        retrieval_reliability=result.retrieval_reliability,  # type: ignore[arg-type]
        fallback_summary=fallback_summary,
        manual_review_summary=manual_review_summary or {},
        needs_human_review=result.needs_human_review,
        approval=_approval_for_policy_status(policy_status),
        pack=GatePackMetadata.model_validate(pack_metadata or None) if pack_metadata else None,
        created_at=datetime.now(timezone.utc),
    )


def _policy_status_for_result(result: CheckResult) -> str:
    s1_fail_count = max(0, result.s1_total - result.s1_passed)
    if s1_fail_count > 0:
        return "block"
    if result.execution_mode == "mixed_execution_modes":
        return "needs_human_review"
    if is_simulation_execution_mode(result.execution_mode):
        return "needs_human_review"
    if result.needs_human_review:
        return "needs_human_review"
    if not result.gate_passed:
        return "needs_human_review"
    if result.gate_status == "warn":
        return "warn"
    return "pass"


def _approval_for_policy_status(policy_status: str) -> dict[str, object]:
    if policy_status == "needs_human_review":
        return {
            "approval_required": True,
            "approval_status": "pending",
            "approver_role": "quality_owner",
        }
    return {
        "approval_required": False,
        "approval_status": "not_required",
        "approver_role": None,
    }


# ------------------------------------------------------------------
# Markdown rendering
# ------------------------------------------------------------------


def _render_customer_report_markdown(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
    pack_metadata: dict[str, Any] | None = None,
) -> str:
    overall_decision = map_overall_decision(result)
    summary = build_customer_report_summary(result)
    case_rows = build_case_report_rows(result, failure_actions)
    target_docs = collect_target_docs(result)
    pack_metadata = pack_metadata or {}
    client_name = (
        str(
            pack_metadata.get("client_name") or pack_metadata.get("tenant_name") or "未設定"
        ).strip()
        or "未設定"
    )
    app_name = (
        str(pack_metadata.get("app_name") or pack_metadata.get("pack_name") or "未設定").strip()
        or "未設定"
    )
    change_event = (
        pack_metadata.get("change_event")
        if report_mode_exposes_sensitive_fields(report_mode)
        else None
    )
    s1_failures = [
        row
        for row in case_rows
        if str(row["severity"]).strip().upper() == "S1" and row["pass_fail"] == "fail"
    ]

    lines = ["# Proof Gate 実行レポート", "", "## 1. 本番反映判定"]
    lines.append(f"- 判定: {_overall_decision_label(overall_decision)}")
    lines.append(f"- policy_status: {_policy_status_for_result(result).upper()}")
    lines.append(f"- summary: {summary['headline']}")

    lines.append("")
    lines.append("## 2. 実行概要")
    lines.append(f"- client_name: {client_name}")
    lines.append(f"- app_name: {app_name}")
    lines.append(f"- run_id: {result.run_id}")
    lines.append(f"- execution_mode: {result.execution_mode}")
    lines.append(f"- current_cases: {summary['total_cases']}")
    lines.append(f"- baseline_runs: {result.baseline_runs}")
    lines.append(f"- aggregation_policy: {result.aggregation_policy}")
    lines.append(f"- needs_human_review: {'YES' if result.needs_human_review else 'NO'}")
    lines.append(f"- judge_fallback_count: {result.judge_fallback_count}")

    lines.append("")
    lines.append("## 3. 対象ドキュメントと変更点")
    if target_docs:
        lines.append(f"- target_docs: {', '.join(target_docs)}")
    else:
        lines.append("- target_docs: 未設定")
    if change_event is None:
        lines.append("- change_event: 未設定")
    else:
        lines.append(f"- change_event: {change_event}")
    provenance = result.run_provenance or {}
    if provenance:
        lines.append(f"- prompt_hash: {provenance.get('prompt_hash') or '未設定'}")
        lines.append(f"- model: {provenance.get('model') or '未設定'}")
        lines.append(
            f"- quality_pack_version: {provenance.get('quality_pack_version') or '未設定'}"
        )

    lines.append("")
    lines.append("## 4. 実行結果サマリ")
    lines.append(f"- overall_pass_rate: {result.overall_rate:.1f}%")
    lines.append(f"- s1_pass_rate: {result.s1_rate:.1f}%")
    lines.append(f"- failed_cases: {summary['failed_cases']}")
    lines.append(f"- s1_failed_cases: {summary['s1_failed_cases']}")
    lines.append(f"- main_failure_category: {summary['main_failure_category']}")

    lines.append("")
    lines.append("## 5. S1重大失敗一覧")
    if s1_failures:
        lines.append("| Case ID | Name | Fail Reason | Next Actions |")
        lines.append("|---------|------|-------------|--------------|")
        for row in s1_failures:
            next_actions = row.get("next_actions") or []
            action_text = (
                "; ".join(_customer_action_label(item) for item in next_actions)
                if next_actions
                else "-"
            )
            lines.append(
                "| {case_id} | {name} | {fail_reason} | {next_actions} |".format(
                    case_id=row["case_id"],
                    name=str(row.get("name") or "-").replace("|", "\\|"),
                    fail_reason=str(
                        row.get("fail_reason") or row.get("safe_reason") or "-"
                    ).replace("|", "\\|"),
                    next_actions=action_text.replace("|", "\\|"),
                )
            )
    else:
        lines.append("- 該当なし")

    lines.append("")
    lines.append("## 6. ケース別結果")
    if case_rows:
        lines.append("| Case ID | Name | Severity | Decision | Pass/Fail | Fail Reason |")
        lines.append("|---------|------|----------|----------|-----------|-------------|")
        for row in case_rows:
            lines.append(
                "| {case_id} | {name} | {severity} | {decision} | {pass_fail} | {fail_reason} |".format(
                    case_id=row["case_id"],
                    name=str(row.get("name") or "-").replace("|", "\\|"),
                    severity=row["severity"],
                    decision=row["decision"],
                    pass_fail=row["pass_fail"],
                    fail_reason=str(
                        row.get("fail_reason") or row.get("safe_reason") or "-"
                    ).replace("|", "\\|"),
                )
            )
    else:
        lines.append("- ケース別の詳細データはありません。")

    lines.append("")
    lines.append("## 7. 推奨アクション")
    action_lines: list[str] = []
    seen_actions: set[str] = set()
    for row in case_rows:
        for action in row.get("next_actions") or []:
            normalized = _customer_action_label(action).strip()
            if not normalized or normalized in seen_actions:
                continue
            seen_actions.add(normalized)
            action_lines.append(normalized)
    if action_lines:
        for action in action_lines:
            lines.append(f"- {action}")
    else:
        lines.append("- 現時点で追加対応は不要です。")

    lines.append("")
    lines.append("## 8. 月額Monitorで継続確認すべき項目")
    lines.append("- FAQ・規約・料金表の更新後にS1ケースを再実行する")
    lines.append("- 返金・解約・料金・契約条件に関する回答を継続確認する")
    lines.append("- プロンプト変更後に高リスクケースを再実行する")
    lines.append("- 新しい問い合わせ傾向に応じて高リスクケースを追加する")
    lines.append("- 月次レポートで重大誤回答リスクと改善状況を確認する")

    lines.append("")
    lines.append("## 9. 運用向け詳細")
    lines.append("以下は運用・開発向けの詳細です。")

    return "\n".join(lines) + "\n"


def _render_gate_operations_markdown(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
    *,
    history_decisions: list[GateDecision] | None = None,
    compare_offset: int = 1,
    trend_window: int = 5,
) -> str:
    """Render the existing operations-focused gate markdown."""
    status = result.gate_status.upper()
    next_actions = _build_structured_next_actions(
        result.failure_categories, failure_actions, result.failure_case_ids
    )
    if result.judge_fallback_count > 0:
        next_actions.append(
            GateNextAction(
                failure_category="judge_reliability",
                count=result.judge_fallback_count,
                action="Re-run judge-enabled evaluation and confirm model/API connectivity",
            )
        )
    if result.embedding_fallback_used:
        next_actions.append(
            GateNextAction(
                failure_category="embedding_reliability",
                count=max(1, result.embedding_fallback_count),
                action="Check embedding dependency/model loading and rebuild the retrieval index",
            )
        )
    if result.needs_human_review:
        next_actions.append(
            GateNextAction(
                failure_category="human_review",
                count=1,
                action="Route this run for manual review before approving the update",
            )
        )

    s1_failure_count = max(0, result.s1_total - result.s1_passed)
    lines = [f"## RAG Quality Gate: {status}\n"]
    lines.append("### Executive Summary")
    lines.append(f"- Production promotion: {_executive_promotion_summary(status)}")
    lines.append(f"- Gate status: {status}")
    lines.append(f"- Policy status: {_policy_status_for_result(result).upper()}")
    lines.append(f"- Execution mode: {result.execution_mode}")
    lines.append(
        f"- S1 pass rate: {result.s1_rate:.1f}% ({s1_failure_count} S1 failure"
        f"{'s' if s1_failure_count != 1 else ''})"
    )
    lines.append(f"- Overall pass rate: {result.overall_rate:.1f}%")
    lines.append(
        f"- Main failure category: {_main_failure_category_summary(result.failure_categories)}"
    )
    if next_actions:
        lines.append(f"- Recommended next action: {next_actions[0].action}")
    else:
        lines.append("- Recommended next action: No immediate action required.")
    lines.append("")
    lines.append(f"- Aggregation Policy: {result.aggregation_policy}")
    lines.append("")
    lines.append("### Gate Policy / 顧客向け判定ルール")
    lines.append("- S1 fail => BLOCK。本番反映せず、原因調査と再実行結果を確認する。")
    lines.append(
        "- S1 judge fallback または judge unavailable => NEEDS_HUMAN_REVIEW。"
        "人手確認が終わるまでは BLOCK 相当として扱う。"
    )
    lines.append("- S2 fail => WARN/REVIEW。影響範囲と修正要否を確認する。")
    lines.append(
        "- S1重大失敗なしの全体しきい値未達 => REVIEW。" "全体品質の低下として人手確認する。"
    )
    lines.append(
        "- PASS は設定済みケースとしきい値の範囲で基準を満たした状態であり、"
        "全回答の完全保証ではない。"
    )

    if history_decisions:
        from .history import build_gate_history_summary_lines

        history_lines = build_gate_history_summary_lines(
            history_decisions,
            compare_offset=compare_offset,
            trend_window=trend_window,
        )
        if history_lines:
            lines.append("\n### Recent History Summary")
            lines.extend(history_lines)

    lines.append("")
    provenance = result.run_provenance or {}
    if provenance:
        lines.append("### Provenance")
        lines.append(f"- Model: {provenance.get('model') or '-'}")
        lines.append(f"- Prompt hash: {provenance.get('prompt_hash') or '-'}")
        lines.append(f"- Prompt version: {provenance.get('prompt_version') or '-'}")
        lines.append(f"- Retrieval config hash: {provenance.get('retrieval_config_hash') or '-'}")
        lines.append(f"- Adapter config hash: {provenance.get('adapter_config_hash') or '-'}")
        lines.append(f"- Index version: {provenance.get('index_version') or '-'}")
        lines.append(f"- Quality pack version: {provenance.get('quality_pack_version') or '-'}")
        lines.append(f"- Case set version: {provenance.get('case_set_version') or '-'}")
        lines.append(f"- Change event id: {provenance.get('change_event_id') or '-'}")
        snapshot_ids = provenance.get("doc_snapshot_ids") or []
        if snapshot_ids:
            lines.append(f"- Doc snapshot ids: {', '.join(str(item) for item in snapshot_ids)}")

    lines.append("| Metric | Actual | Threshold | Status |")
    lines.append("|--------|--------|-----------|--------|")
    for t in result.thresholds:
        if not t.passed:
            icon = "NG"
        elif t.warned:
            icon = "WARN"
        else:
            icon = "OK"
        lines.append(f"| {t.name} | {t.actual:.1f}% | {t.threshold:.1f}% | {icon} |")

    observed_metrics: list[tuple[str, float, int]] = []
    if result.avg_faithfulness is not None:
        observed_metrics.append(
            ("Avg faithfulness", result.avg_faithfulness, result.faithfulness_scored)
        )
    if result.avg_judge_relevance is not None:
        observed_metrics.append(
            (
                "Avg judge relevance",
                result.avg_judge_relevance,
                result.judge_relevance_scored,
            )
        )
    if result.avg_evidence_recall is not None:
        observed_metrics.append(
            (
                "Avg expected evidence recall",
                result.avg_evidence_recall,
                result.evidence_recall_scored,
            )
        )

    if observed_metrics:
        lines.append("\n### Observed Metrics")
        lines.append("| Metric | Average | Scored Runs |")
        lines.append("|--------|---------|-------------|")
        for name, actual, scored in observed_metrics:
            lines.append(f"| {name} | {actual:.1f}% | {scored} |")

    lines.append("\n### Reliability")
    lines.append(f"- Judge reliability: {result.judge_reliability.upper()}")
    lines.append(f"- Judge fallback count: {result.judge_fallback_count}")
    if result.judge_failure_types:
        judge_failure_summary = ", ".join(
            f"{failure_type}={count}" for failure_type, count in result.judge_failure_types.items()
        )
        lines.append(f"- Judge failure types: {judge_failure_summary}")
    lines.append(f"- Embedding fallback: {'YES' if result.embedding_fallback_used else 'NO'}")
    if result.embedding_fallback_reason:
        lines.append(f"- Embedding fallback reason: {result.embedding_fallback_reason}")
    lines.append(f"- Retrieval reliability: {result.retrieval_reliability.upper()}")
    lines.append(f"- Needs human review: {'YES' if result.needs_human_review else 'NO'}")

    if result.fresh_case_review_rate is not None and result.stale_after_days > 0:
        lines.append("\n### Case Staleness")
        lines.append(
            "- Fresh review rate: "
            f"{result.fresh_case_review_rate:.1f}% "
            f"({result.fresh_case_count}/{result.fresh_case_total}) "
            f"within {result.stale_after_days} days"
        )
        if result.stale_cases:
            lines.append("")
            lines.append("| Case | Severity | Owner | Reference | Age Days | Issue |")
            lines.append("|------|----------|-------|-----------|----------|-------|")
            for item in result.stale_cases:
                owner = item.owner or "-"
                reference = item.reference_field
                if item.reference_value:
                    reference = f"{reference}={item.reference_value}".strip("=")
                age_days = str(item.age_days) if item.age_days is not None else "-"
                issue = item.issue.replace("|", "\\|")
                lines.append(
                    f"| {item.case_id} | {item.severity} | {owner} | {reference or '-'} | {age_days} | {issue} |"
                )
        else:
            lines.append("- No stale active cases detected.")

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

    if next_actions:
        lines.append("\n### Next Actions")
        lines.append("| Failure Category | Affected Cases | Next Action | Owner | Due |")
        lines.append("|------------------|----------------|-------------|-------|-----|")
        for action in next_actions:
            safe_action = action.action.replace("|", "\\|")
            cases_str = ", ".join(action.affected_case_ids) if action.affected_case_ids else "-"
            lines.append(
                f"| {action.failure_category} | {cases_str} | {safe_action} | {action.owner} | {action.due} |"
            )

    return "\n".join(lines) + "\n"


def _render_customer_report_markdown_clean(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
    pack_metadata: dict[str, Any] | None = None,
    *,
    report_mode: str = "full",
) -> str:
    overall_decision = map_overall_decision(result)
    summary = build_customer_report_summary(result)
    case_rows = build_case_report_rows(
        result,
        failure_actions,
        report_mode=report_mode,
        artifact_type=ArtifactType.CUSTOMER_SUMMARY,
    )
    target_docs = collect_target_docs_if_report_mode_allows(result, report_mode)
    pack_metadata = pack_metadata or {}
    client_name = str(pack_metadata.get("client_name") or "未設定").strip() or "未設定"
    app_name = str(pack_metadata.get("app_name") or "未設定").strip() or "未設定"
    change_event = pack_metadata.get("change_event")
    s1_failures = [
        row
        for row in case_rows
        if str(row["severity"]).strip().upper() == "S1" and row["pass_fail"] == "fail"
    ]

    lines = ["# Proof Gate 実行レポート", "", "## 1. 本番反映判定"]
    lines.append(f"- 判定: {_overall_decision_label(overall_decision)}")
    lines.append(f"- policy_status: {_policy_status_for_result(result).upper()}")
    lines.append(f"- summary: {summary['headline']}")

    lines.append("")
    lines.append("## 2. 実行概要")
    lines.append(f"- client_name: {client_name}")
    lines.append(f"- app_name: {app_name}")
    lines.append(f"- run_id: {result.run_id}")
    lines.append(f"- execution_mode: {result.execution_mode}")
    lines.append(f"- current_cases: {summary['total_cases']}")
    lines.append(f"- baseline_runs: {result.baseline_runs}")
    lines.append(f"- aggregation_policy: {result.aggregation_policy}")
    lines.append(f"- needs_human_review: {'YES' if result.needs_human_review else 'NO'}")
    lines.append(f"- judge_fallback_count: {result.judge_fallback_count}")

    lines.append("")
    lines.append("## 3. 対象ドキュメントと変更点")
    if target_docs:
        lines.append(f"- target_docs: {', '.join(target_docs)}")
    else:
        lines.append("- target_docs: 未設定")
    if change_event is None:
        lines.append("- change_event: 未設定")
    else:
        lines.append(f"- change_event: {change_event}")
    provenance = result.run_provenance or {}
    if provenance:
        lines.append(f"- prompt_hash: {provenance.get('prompt_hash') or '未設定'}")
        lines.append(f"- model: {provenance.get('model') or '未設定'}")
        lines.append(
            f"- quality_pack_version: {provenance.get('quality_pack_version') or '未設定'}"
        )

    lines.append("")
    lines.append("## 4. 実行結果サマリ")
    lines.append(f"- overall_pass_rate: {result.overall_rate:.1f}%")
    lines.append(f"- s1_pass_rate: {result.s1_rate:.1f}%")
    lines.append(f"- failed_cases: {summary['failed_cases']}")
    lines.append(f"- s1_failed_cases: {summary['s1_failed_cases']}")
    lines.append(f"- main_failure_category: {summary['main_failure_category']}")

    lines.append("")
    lines.append("## 5. S1重大失敗一覧")
    if s1_failures:
        lines.append("| Case ID | Name | Fail Reason | Next Actions |")
        lines.append("|---------|------|-------------|--------------|")
        for row in s1_failures:
            next_actions = row.get("next_actions") or []
            action_text = (
                "; ".join(_customer_action_label(item) for item in next_actions)
                if next_actions
                else "-"
            )
            lines.append(
                "| {case_id} | {name} | {fail_reason} | {next_actions} |".format(
                    case_id=row["case_id"],
                    name=str(row.get("name") or "-").replace("|", "\\|"),
                    fail_reason=str(
                        row.get("fail_reason") or row.get("safe_reason") or "-"
                    ).replace("|", "\\|"),
                    next_actions=action_text.replace("|", "\\|"),
                )
            )
    else:
        lines.append("- 該当なし")

    lines.append("")
    lines.append("## 6. ケース別結果")
    if case_rows:
        lines.append("| Case ID | Name | Severity | Decision | Pass/Fail | Fail Reason |")
        lines.append("|---------|------|----------|----------|-----------|-------------|")
        for row in case_rows:
            lines.append(
                "| {case_id} | {name} | {severity} | {decision} | {pass_fail} | {fail_reason} |".format(
                    case_id=row["case_id"],
                    name=str(row.get("name") or "-").replace("|", "\\|"),
                    severity=row["severity"],
                    decision=row["decision"],
                    pass_fail=row["pass_fail"],
                    fail_reason=str(
                        row.get("fail_reason") or row.get("safe_reason") or "-"
                    ).replace("|", "\\|"),
                )
            )
    else:
        lines.append("- ケース別の詳細データはありません。")

    lines.append("")
    lines.append("## 7. 推奨アクション")
    action_lines: list[str] = []
    seen_actions: set[str] = set()
    for row in case_rows:
        for action in row.get("next_actions") or []:
            normalized = _customer_action_label(action).strip()
            if not normalized or normalized in seen_actions:
                continue
            seen_actions.add(normalized)
            action_lines.append(normalized)
    if action_lines:
        for action in action_lines:
            lines.append(f"- {action}")
    else:
        lines.append("- 現時点で追加対応は不要です。")

    lines.append("")
    lines.append("## 8. 月額Monitorで継続確認すべき項目")
    lines.append("- FAQ・規約・料金表の更新後にS1ケースを再実行する")
    lines.append("- 返金・解約・料金・契約条件に関する回答を継続確認する")
    lines.append("- プロンプト変更後に高リスクケースを再実行する")
    lines.append("- 新しい問い合わせ傾向に応じて高リスクケースを追加する")
    lines.append("- 月次レポートで重大誤回答リスクと改善状況を確認する")

    lines.append("")
    lines.append("## 9. 運用向け詳細")
    lines.append("以下は運用・開発向けの詳細です。")

    return "\n".join(lines) + "\n"


def render_gate_markdown(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
    *,
    pack_metadata: dict[str, Any] | None = None,
    history_decisions: list[GateDecision] | None = None,
    compare_offset: int = 1,
    trend_window: int = 5,
    report_mode: str = "full",
) -> str:
    """Render a gate check result as customer-facing Markdown plus ops details."""
    normalized_report_mode = normalize_report_mode(report_mode)
    if normalized_report_mode != "full":
        return render_gate_safe_summary_markdown(result, report_mode=normalized_report_mode)
    customer_markdown_lines = []
    append_simulation_warning(customer_markdown_lines, result.execution_mode)
    customer_markdown = _render_customer_report_markdown_clean(
        result,
        failure_actions=failure_actions,
        pack_metadata=pack_metadata,
        report_mode=normalized_report_mode,
    )
    operations_markdown = _render_gate_operations_markdown(
        result,
        failure_actions=failure_actions,
        history_decisions=history_decisions,
        compare_offset=compare_offset,
        trend_window=trend_window,
    )
    prefix = "\n".join(customer_markdown_lines).strip()
    if prefix:
        prefix = prefix + "\n\n"
    return prefix + customer_markdown.rstrip() + "\n\n" + operations_markdown.lstrip()


def render_customer_summary_markdown(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
    *,
    pack_metadata: dict[str, Any] | None = None,
    report_mode: str = "redacted",
) -> str:
    """Render a customer-safe summary distinct from the internal report."""
    normalized_report_mode = normalize_report_mode(report_mode)
    if normalized_report_mode == "ci":
        normalized_report_mode = "redacted"
    lines = ["# Proof Gate Customer Summary", ""]
    append_simulation_warning(lines, result.execution_mode)
    lines.extend(
        [
            "## Scope And Meaning",
            "",
            f"- execution_mode: {result.execution_mode}",
            f"- report_mode: {normalized_report_mode}",
            (
                "- PASS means the configured checks passed for the specified cases, "
                "documents, model, and settings in this run."
            ),
            "- PASS does not guarantee overall production safety, legal compliance, or correctness for all questions.",
            "- S1 outcomes still require human review when the run is uncertain, simulated, or fallback-driven.",
            "",
        ]
    )
    lines.append(
        _render_customer_report_markdown_clean(
            result,
            failure_actions=failure_actions,
            pack_metadata=pack_metadata,
            report_mode=normalized_report_mode,
        ).strip()
    )
    return "\n".join(lines) + "\n"


def render_gate_safe_summary_markdown(result: CheckResult, *, report_mode: str) -> str:
    """Render aggregate-only gate output for CI/redacted report modes."""
    summary = build_customer_report_summary(result)
    status = result.gate_status.upper()
    policy_status = _policy_status_for_result(result).upper()
    s1_failure_count = max(0, result.s1_total - result.s1_passed)
    lines = [
        "# Proof Gate Safe Summary",
        "",
        f"- report_mode: {normalize_report_mode(report_mode)}",
        f"- execution_mode: {result.execution_mode}",
        f"- gate_status: {status}",
        f"- policy_status: {policy_status}",
        f"- run_id: {result.run_id}",
        f"- total_cases: {summary['total_cases']}",
        f"- passed_cases: {summary['passed_cases']}",
        f"- failed_cases: {summary['failed_cases']}",
        f"- s1_failed_cases: {s1_failure_count}",
        f"- overall_pass_rate: {result.overall_rate:.1f}%",
        f"- s1_pass_rate: {result.s1_rate:.1f}%",
        f"- aggregation_policy: {result.aggregation_policy}",
        f"- main_failure_category: {summary['main_failure_category']}",
        f"- needs_human_review: {'YES' if result.needs_human_review else 'NO'}",
        f"- judge_fallback_count: {result.judge_fallback_count}",
    ]
    if is_simulation_execution_mode(result.execution_mode):
        lines.extend(["", SIMULATION_WARNING_EN, SIMULATION_WARNING_JA])
    return "\n".join(lines) + "\n"
