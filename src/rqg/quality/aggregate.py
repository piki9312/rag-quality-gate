"""集計ユーティリティ — パス率・レイテンシ・コスト集計。"""

from __future__ import annotations

import math
from typing import Any


def severity_pass_rate(
    results: list, severity: str
) -> tuple[float, int, int]:
    """特定 severity のパス率を計算する。"""
    filtered = [r for r in results if r.severity == severity]
    total = len(filtered)
    passed = sum(1 for r in filtered if r.passed)
    rate = (passed / total * 100) if total else 0.0
    return rate, passed, total


def case_pass_rates(results: list) -> dict[str, float]:
    """case_id ごとのパス率を計算する。"""
    stats: dict[str, tuple[int, int]] = {}
    for r in results:
        p, t = stats.get(r.case_id, (0, 0))
        p += 1 if r.passed else 0
        t += 1
        stats[r.case_id] = (p, t)
    return {cid: (p / t if t > 0 else 0.0) for cid, (p, t) in stats.items()}


def percentile(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = max(0, math.ceil((pct / 100) * len(values)) - 1)
    return values[idx]


def failure_breakdown(results: list) -> dict[str, int]:
    """failure_type ごとのカウント。"""
    breakdown: dict[str, int] = {}
    for r in results:
        if r.passed:
            continue
        ft = r.failure_type or "unknown"
        breakdown[ft] = breakdown.get(ft, 0) + 1
    return dict(sorted(breakdown.items(), key=lambda x: -x[1]))
