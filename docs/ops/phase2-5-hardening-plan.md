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
- Measurement Conditions (for WS1 Target):
  - 対象は sample repo への導入（例: `packs/hr` ベース）
  - 既存顧客 repo への組み込みは別トラックで測定し、本 target の判定対象外とする
  - 初回ケース設計・ケース追加の作業時間は除外し、導入/運用フロー時間のみを計測する
  - 初回導入時間は「手順開始」から「初回 gate 実行結果の確認完了」までを計測する
  - 週次運用時間は「週次更新開始」から「週次レポート確認完了」までを計測する
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
- Completion record: docs/ops/phase2-5-first-sprint-completion-record.md

## 5. Weekly Metrics (Phase2.5)

- M1 onboarding_time_minutes
- M2 weekly_ops_time_minutes
- M3 failure_action_coverage_rate
- M4 gate_exception_count
- M5 overdue_exceptions_count
- Automation: .github/workflows/phase2-5-weekly-metrics.yml がレジスタ更新 PR を自動作成

## 5.1 Near-term Operational Controls

- failure category ごとの推奨アクションを WS2 テンプレートで標準化
- investigate 発生時は標準対応フローに従って issue 駆動で対応
- override / warn-only / no-data は WS3 strict controls で制御
- case品質レビューは週次 issue とチェックリストで定例化
- onboarding / weekly ops 実測値は weekly register へ継続蓄積

## 6. Ownership

- Phase owner: quality owner
- Ops owner: release owner
- Review approver: domain owner

## 7. Related Files

- docs/ops/execution-template-charter-kpi-weekly.md
- docs/ops/phase2-weekly-metrics-register.md
- docs/ops/phase2-kickoff-board.md
- docs/ops/phase2-5-ws1-baseline-sheet.md
- docs/ops/phase2-5-ws2-failure-review-template.md
- docs/ops/phase2-5-ws3-gate-exception-approval-template.md
- docs/ops/phase2-5-weekly-metrics-register.md
- docs/ops/phase2-5-first-sprint-completion-record.md
- docs/ops/phase2-5-investigate-response-flow.md
- docs/ops/phase2-5-case-quality-weekly-review.md
- .github/workflows/phase2-5-weekly-metrics.yml
- .github/workflows/phase2-5-weekly-review-issue.yml
