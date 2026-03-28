# Phase2.5 WS2 Failure Review Template

WS2 (Failure reason to action loop) を週次で運用するための記録テンプレートです。

## 1. Purpose

- fail 原因をカテゴリで記録する
- 各 fail に再発防止アクションを紐付ける
- 次週レビューでアクション完了を確認する

## 2. Failure Categories (fixed)

- retrieval_miss: 参照すべき根拠が取得されない
- stale_source: 古い根拠を参照している
- synthesis_error: 根拠はあるが回答統合が不適切
- tool_failure: パイプライン/実行基盤の失敗
- policy_violation: 制約違反・禁止事項違反
- other: 上記以外（必ず補足説明を記載）

## 3. Weekly Review Log

| week_start | run_or_pr | failure_category | incident_summary | root_cause_hypothesis | action_owner | due_date | action_status | verified_next_week | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | run id / PR | retrieval_miss | short summary | hypothesis | owner | YYYY-MM-DD | open / in-progress / done | yes / no | memo |

## 4. Coverage Metric

- failure_action_coverage_rate = (action_owner と due_date が設定された fail 件数) / (fail 総件数)
- Target: 週次で 100% 記録

## 5. Weekly Review Checklist

- [ ] 今週の fail をカテゴリ分類した
- [ ] 全 fail に action_owner と due_date を設定した
- [ ] 先週 carry-over の action_status を更新した
- [ ] verified_next_week を判定した