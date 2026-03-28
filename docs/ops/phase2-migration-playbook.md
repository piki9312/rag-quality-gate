# Phase2 Migration Playbook

Phase2 は「互換維持」から「旧形式の計画的削減」に移行するための運用フェーズです。
このドキュメントは、Phase2 開始前に固定する運用ルールを定義します。

関連ファイル:

- docs/ops/phase2-kickoff-board.md
- .github/workflows/phase2-weekly-metrics.yml
- docs/ops/phase2-weekly-metrics-register.md
- .github/PULL_REQUEST_TEMPLATE/issue4-post-expiry-cleanup.md

## 1. Phase2 開始条件

次をすべて満たした時点で Phase2 を開始します。

- 対象ケースの母集団が確定している
- 週次計測の指標が定義され、計測手順が固定されている
- migrate-cases の実施手順とロールバック条件が定義されている
- 期限後互換撤去タスクの担当者と実行タイミングが確定している

## 2. 対象母集団の固定

以下のテンプレートを使って対象を登録します。

| case_source | format | owner | baseline_impacted_cases | baseline_unresolved_refs | target_zero_date | status |
| --- | --- | --- | ---: | ---: | --- | --- |
| packs/hr/cases.csv | csv | hr-team | 0 | 0 | 2026-06-15 | planned |
| packs/demo_cycle/cases.csv | csv | demo-team | 0 | 0 | 2026-06-15 | planned |
| (add your file) | json/csv | team-name | 0 | 0 | YYYY-MM-DD | planned |

備考:

- baseline_impacted_cases: impact 実行結果の impacted_case_ids 件数
- baseline_unresolved_refs: migrate-cases の unresolved_legacy_refs

運用開始済みの記録は `docs/ops/phase2-kickoff-board.md` を参照してください。

## 3. 指標定義（週次）

週次で次の指標を収集します。

- M1 impacted_case_count
  - 定義: impact_report.json の impacted_case_ids 件数
  - 目標: 想定外の急増がないこと
- M2 unresolved_legacy_refs
  - 定義: migrate-cases レポートの unresolved_legacy_refs
  - 目標: 常時 0

週次計測は GitHub Actions `Phase2 Weekly Migration Metrics` で自動実行できます。
結果の定例転記は `docs/ops/phase2-weekly-metrics-register.md` を使用してください。

## 4. 週次運用手順

1. 現在ケースをバックアップ

```bash
cp artifacts/eval_cases.json artifacts/eval_cases.before_migration.json
```

2. 移行実行

```bash
rqg migrate-cases \
  --cases artifacts/eval_cases.json \
  --snapshot artifacts/old_snapshot.json \
  --snapshot-dir index/snapshots \
  --output artifacts/eval_cases.migrated.json \
  --report artifacts/migration_report.json
```

3. 影響確認

```bash
qgate impact \
  --old-snapshot artifacts/old_snapshot.json \
  --new-snapshot artifacts/new_snapshot.json \
  --cases artifacts/eval_cases.migrated.json \
  --output artifacts/impact_report.json
```

4. 評価とゲートを再実行

```bash
rqg eval packs/hr/cases.csv --docs packs/hr/documents/ --mock --index-dir index --log-dir runs/quality
rqg check --log-dir runs/quality --config .rqg.yml
```

## 5. 変更適用/ロールバック条件

変更適用条件:

- migration_report.json の unresolved_legacy_refs が 0
- impact_report.json の結果が想定内
- eval/check が通過

ロールバック条件:

- unresolved_legacy_refs > 0
- impact で重大ケースの想定外 fail が発生
- 評価結果が許容閾値を下回る

ロールバック手順:

1. バックアップケースに戻す
2. 影響ケースをレビュー対象に登録
3. 修正後に再度 migrate-cases を実行

## 6. 担当と期限

- Migration owner: quality owner
- Review approver: domain owner
- Deadline manager: release owner

期限関連:

- 互換有効期間: 2026-03-27 から 2026-06-30
- 互換撤去タスク: https://github.com/piki9312/rag-quality-gate/issues/4

期限後撤去PRを作成する際は
`.github/PULL_REQUEST_TEMPLATE/issue4-post-expiry-cleanup.md` を本文テンプレートとして使用してください。

## 7. Phase2 完了判定

次を満たしたら Phase2 完了とします。

- 主要ケースソースの impacted_case_count が想定レンジで安定
- unresolved_legacy_refs が連続 0
- impact 運用が定常化
- 期限後撤去 PR が作成・マージ済み
