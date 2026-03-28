# Phase2.5 WS3 Gate Exception Approval Template

WS3 (Gate anti-erosion controls) を運用で機能させるための、
期限付き・承認付き例外テンプレートです。

## 1. Rule (fixed)

- 例外は必ず期限付きにする
- 例外は必ず承認者を設定する
- 例外理由と影響範囲を記録する
- 期限超過の例外は無効とし、継続には再承認が必要

## 2. Exception Categories

- warn_only_override: fail を一時的に warn 相当で運用する例外
- no_data_temporary: データ未整備により一時的に no-data を許容する例外
- manual_override: 運用判断で一時的に gate 判定を上書きする例外

## 3. Exception Request Record

| request_id | requested_date | category | affected_scope | reason | requested_by | approver | approved_date | expires_at | status | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EX-YYYYMMDD-001 | YYYY-MM-DD | warn_only_override / no_data_temporary / manual_override | repo/path, workflow, case source | short reason | owner | approver | YYYY-MM-DD | YYYY-MM-DD | active / expired / revoked | issue/pr/run URL |

## 4. Approval Checklist

- [ ] category が定義済み値か確認した
- [ ] reason と affected_scope が具体的に記録されている
- [ ] 代替策または解消計画がある
- [ ] expires_at が設定されている
- [ ] approver が明示されている

## 5. Expiry Check Procedure (weekly)

1. status=active の例外を一覧化する。
2. expires_at < today のレコードを overdue と判定する。
3. overdue を発見した場合:
   - status を expired に更新
   - 当該例外を無効化する対応チケットを作成
   - 週次レビューに記録する

## 6. Audit Log Fields

週次レビューまたは監査ログに最低限残す項目:

- request_id
- category
- approved_date
- expires_at
- status
- approver
- last_reviewed_date
- linked_evidence

## 7. Metrics Mapping

- gate_exception_count: status=active の件数
- overdue_exceptions_count: expires_at 超過かつ status=active の件数

## 8. Weekly Review Summary (template)

| week_start | active_exceptions | overdue_exceptions | actions_taken | reviewer |
| --- | ---: | ---: | --- | --- |
| YYYY-MM-DD | 0 | 0 | summary | owner-name |