# Phase2.5 Investigate Response Flow

Phase2.5 週次メトリクスで decision=investigate が発生した場合の標準対応フローです。

## 1. Trigger

次のいずれかを満たした場合に investigate を発火します。

- M1 onboarding_time_minutes が欠損
- M2 weekly_ops_time_minutes が欠損
- M3 failure_action_coverage_rate < 1.0
- M5 overdue_exceptions_count > 0

## 2. Standard Timeline

### T+0 (same day)

- investigate issue を作成
- run_url と summary.json を issue に添付
- owner/reviewer/期限を確定

### T+1 business day

- 原因を WS1/WS2/WS3 のどこで発生したか分類
- 一時対応と恒久対応を分離
- 影響範囲を記録

### T+3 business days

- 恒久対応を実装
- 再実行して decision を再判定
- 再発防止アクションを WS2 に追記

### T+5 business days

- close criteria を満たしていれば issue close
- 満たさない場合は期限延長理由を明記し、review approver 承認を取得

## 3. Required Issue Fields

- week_start
- run_id
- run_url
- metric values (M1-M5)
- root_cause_hypothesis
- workaround
- permanent_fix
- owner
- due_date
- verification_evidence

## 4. Close Criteria

- 再実行で decision=keep-going
- overdue_exceptions_count=0
- failure_action_coverage_rate=1.0
- 影響したカテゴリの再発防止アクションが WS2 ログに記録済み

## 5. Related Files

- docs/ops/phase2-5-weekly-metrics-register.md
- docs/ops/phase2-5-ws2-failure-review-template.md
- docs/ops/phase2-5-ws3-gate-exception-approval-template.md
