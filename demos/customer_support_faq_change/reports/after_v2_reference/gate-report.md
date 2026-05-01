# Proof Gate 実行レポート

## 1. 本番反映判定
- 判定: 要確認
- policy_status: NEEDS_HUMAN_REVIEW
- summary: 要確認。警告条件または信頼性低下があるため、人手確認後に判断してください。

## 2. 実行概要
- client_name: 未設定
- app_name: 未設定
- run_id: 3449f46b-993
- current_cases: 6
- baseline_runs: 0
- aggregation_policy: latest_run
- needs_human_review: YES
- judge_fallback_count: 0

## 3. 対象ドキュメントと変更点
- target_docs: demo_faq.md
- change_event: 未設定

## 4. 実行結果サマリ
- overall_pass_rate: 100.0%
- s1_pass_rate: 100.0%
- failed_cases: 0
- s1_failed_cases: 0
- main_failure_category: None

## 5. S1重大失敗一覧
- 該当なし

## 6. ケース別結果
| Case ID | Name | Severity | Decision | Pass/Fail | Fail Reason |
|---------|------|----------|----------|-----------|-------------|
| customer_support_faq_001 | キャンペーン商品の返金条件 | S1 | needs_confirmation | pass | - |
| customer_support_faq_002 | 無料トライアル解約期限 | S1 | needs_confirmation | pass | - |
| customer_support_faq_003 | 年額契約の自動更新通知 | S1 | needs_confirmation | pass | - |
| customer_support_faq_004 | 料金ページの確認先 | S2 | needs_confirmation | pass | - |
| customer_support_faq_005 | 解約後のデータ保持 | S2 | needs_confirmation | pass | - |
| customer_support_faq_006 | 契約変更の反映条件 | S2 | needs_confirmation | pass | - |

## 7. 推奨アクション
- 検索モデルまたは依存関係を確認し、必要に応じて検索インデックスを再作成する
- このケースは人手で確認してから更新を承認する

## 8. 月額Monitorで継続確認すべき項目
- FAQ・規約・料金表の更新後にS1ケースを再実行する
- 返金・解約・料金・契約条件に関する回答を継続確認する
- プロンプト変更後に高リスクケースを再実行する
- 新しい問い合わせ傾向に応じて高リスクケースを追加する
- 月次レポートで重大誤回答リスクと改善状況を確認する

## 9. 運用向け詳細
以下は運用・開発向けの詳細です。

## RAG Quality Gate: PASS

### Executive Summary
- Production promotion: Recommended. This pack meets the configured gate thresholds.
- Gate status: PASS
- Policy status: NEEDS_HUMAN_REVIEW
- S1 pass rate: 100.0% (0 S1 failures)
- Overall pass rate: 100.0%
- Main failure category: None
- Recommended next action: Check embedding dependency/model loading and rebuild the retrieval index

- Aggregation Policy: latest_run

### Recent History Summary
- Latest status: PASS (3449f46b-993)
- Current streak: PASS x1
- Overall pass rate trend: 100.0% -> 100.0% (0.0 pts)
- S1 pass rate trend: 100.0% -> 100.0% (0.0 pts)
- Failure action coverage (last 1): 2/2 categories (100.0%)
- Judge reliability: HIGH
- Embedding fallback: YES (model_load_error)
- Needs human review: YES

| Metric | Actual | Threshold | Status |
|--------|--------|-----------|--------|
| S1 pass rate | 100.0% | 100.0% | OK |
| Overall pass rate | 100.0% | 85.0% | OK |
| Avg evidence recall | 100.0% | 70.0% | OK |
| Fresh case review rate | 100.0% | 80.0% | OK |

### Observed Metrics
| Metric | Average | Scored Runs |
|--------|---------|-------------|
| Avg faithfulness | 80.0% | 6 |
| Avg judge relevance | 100.0% | 6 |
| Avg evidence recall | 100.0% | 6 |

### Reliability
- Judge reliability: HIGH
- Judge fallback count: 0
- Embedding fallback: YES
- Embedding fallback reason: model_load_error
- Retrieval reliability: HIGH
- Needs human review: YES

### Case Staleness
- Fresh review rate: 100.0% (6/6) within 45 days
- No stale active cases detected.

### Next Actions
| Failure Category | Affected Cases | Next Action | Owner | Due |
|------------------|----------------|-------------|-------|-----|
| embedding_reliability | - | Check embedding dependency/model loading and rebuild the retrieval index | T.B.D. | T.B.D. |
| human_review | - | Route this run for manual review before approving the update | T.B.D. | T.B.D. |
