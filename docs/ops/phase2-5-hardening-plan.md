# Phase2.5 Hardening Plan

Phase2.5 は「実運用で壊れにくくする」ための開発フェーズです。

## 1. Goal

- Goal A: 導入障壁の主要ボトルネックを継続的に削減する
- Goal B: 運用時の fail 原因を分類し、再発防止までつなげる
- Goal C: ゲート形骸化を防ぐ運用ルールを定着させる

## 2. Exit Criteria

Phase2.5 の完了条件:

- 導入障壁の主要ボトルネックが改善されている
- 運用時の fail 原因が分類され、改善アクションに接続されている
- ゲート形骸化対策が定義され、週次でレビューされている

## 3. Workstreams

### WS1: Onboarding/Ops bottleneck reduction

- Baseline:
  - 初回導入所要時間
  - 週次運用所要時間
- Target:
  - 初回導入: 30分以内
  - 週次運用: 15分以内
- Artifacts:
  - README 導線改善
  - テンプレート更新

### WS2: Failure reason to action loop

- Baseline:
  - failure_category 別件数
  - 再発率
- Target:
  - 週次でカテゴリ別アクションを 100% 記録
- Artifacts:
  - 失敗カテゴリ別プレイブック
  - 週次レビュー反映テンプレート

### WS3: Gate anti-erosion controls

- Baseline:
  - warn-only 例外件数
  - no-data 実行件数
  - 運用での手動override件数
- Target:
  - 例外は期限付き・承認付きのみ
- Artifacts:
  - 例外承認ルール
  - 期限切れチェック
  - 監査ログ項目

## 4. First Sprint (2 weeks)

- Task 1: Bottleneck baseline measurement sheet を追加
- Task 2: Failure category weekly review section を追加
- Task 3: Gate 例外承認テンプレートを追加
- Task 4: 週次レビューで Phase2.5 指標を運用開始

## 5. Weekly Metrics (Phase2.5)

- M1 onboarding_time_minutes
- M2 weekly_ops_time_minutes
- M3 failure_action_coverage_rate
- M4 gate_exception_count
- M5 overdue_exceptions_count

## 6. Ownership

- Phase owner: quality owner
- Ops owner: release owner
- Review approver: domain owner

## 7. Related Files

- docs/ops/execution-template-charter-kpi-weekly.md
- docs/ops/phase2-weekly-metrics-register.md
- docs/ops/phase2-kickoff-board.md
