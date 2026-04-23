"""Gate check — ベースライン比較 + 閾値判定 → pass/fail。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from rqg.domain import GateDecision, GateNextAction, GatePackMetadata

from .aggregate import case_pass_rates, failure_category_breakdown, failure_category_case_ids
from .models import QARunRecord
from .staleness import CaseStalenessItem, summarize_case_staleness

logger = logging.getLogger(__name__)

VALID_AGGREGATION_POLICIES = {"latest_run", "window"}


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


# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------


@dataclass
class GateConfig:
    """品質ゲートの閾値設定。"""

    s1_pass_rate: float = 100.0
    overall_pass_rate: float = 80.0
    retrieval_precision_threshold: float = 0.0  # 0 = チェックしない
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
            retrieval_precision_threshold=th.get("retrieval_precision", 0.0),
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
    needs_human_review: bool = False

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
    needs_human_review = (
        judge_fallback_count > 0 or embedding_fallback_count > 0 or judge_relevance_scored < total
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
                name="Avg evidence recall",
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
        needs_human_review=needs_human_review,
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


def build_gate_decision(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
    pack_metadata: dict[str, Any] | None = None,
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
    metrics["evidence_recall_scored_runs"] = float(result.evidence_recall_scored)
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

    return GateDecision(
        run_id=result.run_id,
        status=status,
        reasons=reasons,
        metrics=metrics,
        next_actions=next_actions,
        judge_fallback_used=result.judge_fallback_count > 0,
        judge_fallback_count=result.judge_fallback_count,
        judge_failure_types=result.judge_failure_types,
        judge_reliability=result.judge_reliability,
        embedding_fallback_used=result.embedding_fallback_used,
        embedding_fallback_count=result.embedding_fallback_count,
        embedding_fallback_reason=result.embedding_fallback_reason,
        needs_human_review=result.needs_human_review,
        pack=GatePackMetadata.model_validate(pack_metadata or None) if pack_metadata else None,
        created_at=datetime.now(timezone.utc),
    )


# ------------------------------------------------------------------
# Markdown rendering
# ------------------------------------------------------------------


def render_gate_markdown(
    result: CheckResult,
    failure_actions: dict[str, str] | None = None,
    *,
    history_decisions: list[GateDecision] | None = None,
    compare_offset: int = 1,
    trend_window: int = 5,
) -> str:
    """Render a gate check result as Markdown."""
    status = result.gate_status.upper()
    lines = [f"## RAG Quality Gate: {status}\n"]
    lines.append(f"- Aggregation Policy: {result.aggregation_policy}")

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
            ("Avg judge relevance", result.avg_judge_relevance, result.judge_relevance_scored)
        )
    if result.avg_evidence_recall is not None:
        observed_metrics.append(
            ("Avg evidence recall", result.avg_evidence_recall, result.evidence_recall_scored)
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
