# Phase2.5 Exit Readiness Check (2026-03-29)

## 1. Purpose

Phase2.5 の Exit Criteria に対して、複数週の運用証跡を横断確認し、
現時点での完了可否を判定する。

## 2. Evidence Scope

- reviewed_at: 2026-03-29 (UTC)
- week_start coverage: 2026-03-09, 2026-03-16, 2026-03-23, 2026-03-28
- fixed gate references:
  - docs/ops/phase2-5-hardening-plan.md (Section 2.1 Provisional Exit Decision Criteria)
  - docs/ops/phase2-5-weekly-metrics-register.md (Weekly Evidence Minimum Set)
- evidence sources:
  - docs/ops/phase2-5-hardening-plan.md
  - docs/ops/phase2-5-weekly-metrics-register.md
  - docs/ops/phase2-5-ws1-baseline-sheet.md
  - docs/ops/phase2-5-ws2-failure-review-template.md
  - docs/ops/phase2-5-ws3-gate-exception-approval-template.md
  - docs/ops/phase2-5-case-quality-weekly-review.md
  - https://github.com/piki9312/rag-quality-gate/actions/runs/23698940469
  - https://github.com/piki9312/rag-quality-gate/actions/runs/23699562524
  - https://github.com/piki9312/rag-quality-gate/actions/runs/23699721101
  - https://github.com/piki9312/rag-quality-gate/pull/33
  - https://github.com/piki9312/rag-quality-gate/pull/34
  - https://github.com/piki9312/rag-quality-gate/issues/28

## 3. Multi-week Metrics Evidence

### 3.1 Register rows used

| week_start | run_id | onboarding_time_minutes | weekly_ops_time_minutes | failure_action_coverage_rate | gate_exception_count | overdue_exceptions_count | decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2026-03-28 | 23675763638 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-23 | 23676386099 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-23 | 23679795825 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-23 | 23698940469 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-16 | 23699562524 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-09 | 23699721101 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |

### 3.2 Week-level summary

| week_start | runs | M1 onboarding (min) | M2 weekly_ops (min) | M3 coverage | M4 active exceptions | M5 overdue exceptions | week decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2026-03-28 | 1 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-23 | 3 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-16 | 1 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-09 | 1 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |

### 3.3 4-week minimum evidence check (E1-E4)

| week_start | E1 row existence | E2 traceability | E3 metric completeness | E4 weekly threshold | evidence status |
| --- | --- | --- | --- | --- | --- |
| 2026-03-28 | pass | pass | pass | pass | pass |
| 2026-03-23 | pass | pass | pass | pass | pass |
| 2026-03-16 | pass | pass | pass | pass | pass |
| 2026-03-09 | pass | pass | pass | pass | pass |

## 4. Exit Criteria Assessment

| criterion (from hardening plan) | evidence | status |
| --- | --- | --- |
| 導入障壁の主要ボトルネックが改善されている | WS1: onboarding 0.25 分、weekly_ops 1.57 分で target(30分/15分)を下回る値を継続 | pass (provisional) |
| 運用時の fail 原因が分類され、改善アクションに接続されている | WS2 weekly log に実 incident を記録。run 23679795825 (tool_failure) -> PR #26 で恒久対処 -> run 23698940469 success で検証 -> PR #29 で運用反映完了 | pass (provisional) |
| ゲート形骸化対策が定義され、週次でレビューされている | WS3 strict controls 定義済み。weekly review issue #28 で checklist 運用を実施 | pass |

## 5. Provisional Exit Decision Gate Check (C1-C4)

| check_id | fixed rule | result | evidence |
| --- | --- | --- | --- |
| C1 | 4 週連続で E1-E4 が pass | pass | week_start 2026-03-09 / 03-16 / 03-23 / 03-28 がすべて pass |
| C2 | 各週 overdue_exceptions_count = 0 | pass | 4 週すべて M5 = 0 |
| C3 | stale timestamp risk = resolved | pass | packs/hr/cases.csv, packs/demo_cycle/cases.csv に last_reviewed_at 列あり。stale rule は case quality weekly review に固定済み |
| C4 | 各週 failure_action_coverage_rate >= 1.00 | pass | 4 週すべて M3 = 1.00 |

## 6. Unresolved Risks

| risk | impact | owner | monitoring |
| --- | --- | --- | --- |
| WS1 計測が sample repo 条件中心 | 既存顧客 repo では導入/運用時間が悪化する可能性 | release owner | 顧客repoトラックで onboarding_time / weekly_ops_time を分離測定し、月次比較する |
| failure_category 母数が週によって少ない | M3 が 1.00 でも検知力が十分でない可能性 | quality owner | fail 件数 0 週が続く場合は synthetic regression を月次で追加実行する |

## 7. Recommendation

- Exit recommendation: proceed to exit decision (provisional)
- Decision note:
  - C1-C4 の fixed rule はすべて pass
  - unresolved risk は残るため、監視付きで provisional 判定を維持する
- Post-exit monitoring:
  1. weekly metrics register の keep-going 連続性を毎週確認する
  2. investigate 判定が発生した場合は Phase2.5 hardening sub-track を再オープンする
