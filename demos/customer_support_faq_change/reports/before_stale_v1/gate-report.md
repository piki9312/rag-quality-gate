# Proof Gate 実行レポート

## 1. 本番反映判定
- 判定: NG
- policy_status: BLOCK
- summary: NG。重大な失敗または block 判定があるため、本番反映は推奨されません。

## 2. 実行概要
- client_name: 未設定
- app_name: 未設定
- run_id: cc15aea9-174
- current_cases: 6
- baseline_runs: 0
- aggregation_policy: latest_run
- needs_human_review: YES
- judge_fallback_count: 0

## 3. 対象ドキュメントと変更点
- target_docs: demo_faq.md
- change_event: 未設定

## 4. 実行結果サマリ
- overall_pass_rate: 16.7%
- s1_pass_rate: 0.0%
- failed_cases: 5
- s1_failed_cases: 3
- main_failure_category: synthesis (5 cases)

## 5. S1重大失敗一覧
| Case ID | Name | Fail Reason | Next Actions |
|---------|------|-------------|--------------|
| customer_support_faq_001 | キャンペーン商品の返金条件 | Keyword match 33% < 80% | 失敗ケースの原因を確認し、週次レビューで対応方針を決める; 本番反映を止め、該当FAQ・規約・回答ロジックを修正する; 検索モデルまたは依存関係を確認し、必要に応じて検索インデックスを再作成する; このケースは人手で確認してから更新を承認する |
| customer_support_faq_002 | 無料トライアル解約期限 | Keyword match 0% < 80% | 失敗ケースの原因を確認し、週次レビューで対応方針を決める; 本番反映を止め、該当FAQ・規約・回答ロジックを修正する; 検索モデルまたは依存関係を確認し、必要に応じて検索インデックスを再作成する; このケースは人手で確認してから更新を承認する |
| customer_support_faq_003 | 年額契約の自動更新通知 | Keyword match 67% < 80% | 失敗ケースの原因を確認し、週次レビューで対応方針を決める; 本番反映を止め、該当FAQ・規約・回答ロジックを修正する; 検索モデルまたは依存関係を確認し、必要に応じて検索インデックスを再作成する; このケースは人手で確認してから更新を承認する |

## 6. ケース別結果
| Case ID | Name | Severity | Decision | Pass/Fail | Fail Reason |
|---------|------|----------|----------|-----------|-------------|
| customer_support_faq_001 | キャンペーン商品の返金条件 | S1 | ng | fail | Keyword match 33% < 80% |
| customer_support_faq_002 | 無料トライアル解約期限 | S1 | ng | fail | Keyword match 0% < 80% |
| customer_support_faq_003 | 年額契約の自動更新通知 | S1 | ng | fail | Keyword match 67% < 80% |
| customer_support_faq_005 | 解約後のデータ保持 | S2 | ng | fail | Keyword match 0% < 50% |
| customer_support_faq_006 | 契約変更の反映条件 | S2 | ng | fail | Keyword match 33% < 50% |
| customer_support_faq_004 | 料金ページの確認先 | S2 | needs_confirmation | pass | - |

## 7. 推奨アクション
- 失敗ケースの原因を確認し、週次レビューで対応方針を決める
- 本番反映を止め、該当FAQ・規約・回答ロジックを修正する
- 検索モデルまたは依存関係を確認し、必要に応じて検索インデックスを再作成する
- このケースは人手で確認してから更新を承認する
- 注意付きで扱い、必要に応じてサポート担当者の確認を入れる

## 8. 月額Monitorで継続確認すべき項目
- FAQ・規約・料金表の更新後にS1ケースを再実行する
- 返金・解約・料金・契約条件に関する回答を継続確認する
- プロンプト変更後に高リスクケースを再実行する
- 新しい問い合わせ傾向に応じて高リスクケースを追加する
- 月次レポートで重大誤回答リスクと改善状況を確認する

## 9. 運用向け詳細
以下は運用・開発向けの詳細です。

## RAG Quality Gate: FAIL

### Executive Summary
- Production promotion: Not recommended. This pack should not be promoted to production.
- Gate status: FAIL
- Policy status: BLOCK
- S1 pass rate: 0.0% (3 S1 failures)
- Overall pass rate: 16.7%
- Main failure category: synthesis (5 cases)
- Recommended next action: Define next action in weekly review issue

- Aggregation Policy: latest_run

### Recent History Summary
- Latest status: FAIL (cc15aea9-174)
- Current streak: FAIL x1
- Overall pass rate trend: 16.7% -> 16.7% (0.0 pts)
- S1 pass rate trend: 0.0% -> 0.0% (0.0 pts)
- Failure action coverage (last 1): 2/3 categories (66.7%)
- Uncovered categories: synthesis (5 cases)
- Judge reliability: HIGH
- Embedding fallback: YES (model_load_error)
- Needs human review: YES

| Metric | Actual | Threshold | Status |
|--------|--------|-----------|--------|
| S1 pass rate | 0.0% | 100.0% | NG |
| Overall pass rate | 16.7% | 85.0% | NG |
| Avg evidence recall | 100.0% | 70.0% | OK |
| Fresh case review rate | 100.0% | 80.0% | OK |

### Observed Metrics
| Metric | Average | Scored Runs |
|--------|---------|-------------|
| Avg faithfulness | 79.7% | 6 |
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

### Per-case Failures
| Case | Actual | Threshold | Name |
|------|--------|-----------|------|
| case:customer_support_faq_001 | 0.0% | 100.0% | キャンペーン商品の返金条件 |
| case:customer_support_faq_002 | 0.0% | 100.0% | 無料トライアル解約期限 |
| case:customer_support_faq_003 | 0.0% | 100.0% | 年額契約の自動更新通知 |
| case:customer_support_faq_005 | 0.0% | 85.0% | 解約後のデータ保持 |
| case:customer_support_faq_006 | 0.0% | 85.0% | 契約変更の反映条件 |

### Failure Categories
| Category | Count |
|----------|-------|
| synthesis | 5 |

### Next Actions
| Failure Category | Affected Cases | Next Action | Owner | Due |
|------------------|----------------|-------------|-------|-----|
| synthesis | customer_support_faq_001, customer_support_faq_002, customer_support_faq_003, customer_support_faq_005, customer_support_faq_006 | Define next action in weekly review issue | T.B.D. | T.B.D. |
| embedding_reliability | - | Check embedding dependency/model loading and rebuild the retrieval index | T.B.D. | T.B.D. |
| human_review | - | Route this run for manual review before approving the update | T.B.D. | T.B.D. |
