# Phase2.5 Exit Readiness Check (2026-03-29)

## 1. Purpose

Phase2.5 の Exit Criteria に対して、複数週の運用証跡を横断確認し、
現時点での完了可否を判定する。

## 2. Evidence Scope

- reviewed_at: 2026-03-29 (UTC)
- week_start coverage: 2026-03-23, 2026-03-28
- evidence sources:
  - docs/ops/phase2-5-hardening-plan.md
  - docs/ops/phase2-5-weekly-metrics-register.md
  - docs/ops/phase2-5-ws1-baseline-sheet.md
  - docs/ops/phase2-5-ws2-failure-review-template.md
  - docs/ops/phase2-5-ws3-gate-exception-approval-template.md
  - docs/ops/phase2-5-case-quality-weekly-review.md
  - https://github.com/piki9312/rag-quality-gate/actions/runs/23698940469
  - https://github.com/piki9312/rag-quality-gate/issues/28

## 3. Multi-week Metrics Evidence

### 3.1 Register rows used

| week_start | run_id | onboarding_time_minutes | weekly_ops_time_minutes | failure_action_coverage_rate | gate_exception_count | overdue_exceptions_count | decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2026-03-28 | 23675763638 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-23 | 23676386099 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-23 | 23679795825 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-23 | 23698940469 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |

### 3.2 Week-level summary

| week_start | runs | M1 onboarding (min) | M2 weekly_ops (min) | M3 coverage | M4 active exceptions | M5 overdue exceptions | week decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2026-03-28 | 1 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |
| 2026-03-23 | 3 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going |

## 4. Exit Criteria Assessment

| criterion (from hardening plan) | evidence | status |
| --- | --- | --- |
| 導入障壁の主要ボトルネックが改善されている | WS1: onboarding 0.25 分、weekly_ops 1.57 分で target(30分/15分)を下回る値を継続 | pass (provisional) |
| 運用時の fail 原因が分類され、改善アクションに接続されている | WS2 template/推奨アクションは定義済み。対象期間は failure row 0 件で、実 incident の closed-loop 証跡は未取得 | partial |
| ゲート形骸化対策が定義され、週次でレビューされている | WS3 strict controls 定義済み。weekly review issue #28 で checklist 運用を実施 | pass |

## 5. Gaps and Risks

- 複数週証跡は 2 週分のみで、運用ばらつき耐性の確認としてはまだ薄い。
- WS2 は「失敗時の運用ループ定義」はあるが、「実失敗を起点にしたクローズド・ループ証跡」が未取得。
- case quality の stale 判定に使う timestamp 列がケース定義にないため、劣化検知の自動性が限定的。

## 6. Recommendation

- Exit recommendation: hold (Phase2.5 継続)
- Exit 判定に進むための最小追加条件:
  1. 異なる week_start で keep-going を最低 2 週分追加
  2. WS2 で少なくとも 1 件、failure_category -> action_owner/due_date -> verified_next_week の完了証跡を記録
  3. case quality の stale 判定基準をデータ項目として明示し、週次レビューで再現可能にする
