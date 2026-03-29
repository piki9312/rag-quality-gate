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

## 3. Recommended Actions (near-term standard)

| failure_category | first action (required) | owner role | due target | completion evidence |
| --- | --- | --- | --- | --- |
| retrieval_miss | 根拠未取得の原因を特定し、index/retrieval 設定を修正 | retrieval owner | 2 business days | rerun result + diff note |
| stale_source | snapshot/source 更新漏れを修正し、再 ingest | data owner | 2 business days | updated snapshot id + rerun |
| synthesis_error | prompt/answer composition を修正し、回帰ケース追加 | quality owner | 3 business days | prompt diff + added case |
| tool_failure | 実行基盤エラーを修正し、再実行手順を記録 | platform owner | 1 business day | run URL + root cause note |
| policy_violation | 制約違反理由を分析し、ガード条件を強化 | domain owner | 2 business days | policy diff + check evidence |
| other | 分類不能理由を記録し、暫定カテゴリでアクション設定 | quality owner | 2 business days | categorized incident note |

## 4. Weekly Review Log

| week_start | run_or_pr | failure_category | incident_summary | root_cause_hypothesis | action_owner | due_date | action_status | verified_next_week | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | run id / PR | retrieval_miss | short summary | hypothesis | owner | YYYY-MM-DD | open / in-progress / done | yes / no | memo |
| 2026-03-23 | run 23679795825 | tool_failure | weekly metrics workflow が register 自動PR作成で失敗し、運用が停止しかけた | repository setting により GitHub Actions の PR 作成が禁止されていた | piki9312 | 2026-03-29 | done | yes | fix: PR #26 (manual PR fallback)。verify: run 23698940469 success。closure: PR #29 merged。 |

## 5. Coverage Metric

- failure_action_coverage_rate = (action_owner と due_date が設定された fail 件数) / (fail 総件数)
- Target: 週次で 100% 記録

## 6. Weekly Review Checklist

- [ ] 今週の fail をカテゴリ分類した
- [ ] 全 fail に action_owner と due_date を設定した
- [ ] 先週 carry-over の action_status を更新した
- [ ] verified_next_week を判定した