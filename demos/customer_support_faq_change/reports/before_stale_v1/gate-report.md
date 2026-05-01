# Proof Gate 実行レポート

## 1. 本番反映判定
- 判定: NG
- policy_status: BLOCK
- summary: NG。重大な失敗または block 判定があるため、本番反映は推奨されません。

## 2. 実行概要
- client_name: demo_customer
- app_name: Customer Support AI Quality Pack
- run_id: ce7d3eb4-63a
- current_cases: 9
- baseline_runs: 0
- aggregation_policy: latest_run
- needs_human_review: NO
- judge_fallback_count: 0

## 3. 対象ドキュメントと変更点
- target_docs: demo_faq.md
- change_event: 未設定

## 4. 実行結果サマリ
- overall_pass_rate: 33.3%
- s1_pass_rate: 0.0%
- failed_cases: 6
- s1_failed_cases: 3
- main_failure_category: synthesis (6 cases)

## 5. S1重大失敗一覧
| Case ID | Name | Fail Reason | Next Actions |
|---------|------|-------------|--------------|
| customer_support_faq_001 | キャンペーン商品の返金条件 | Keyword match 33% < 80% | Define next action in weekly review issue; block; Route this case for manual review before approving the update |
| customer_support_faq_006 | 無料トライアル解約の締切 | Keyword match 0% < 80% | Define next action in weekly review issue; block; Route this case for manual review before approving the update |
| customer_support_faq_007 | 年額プラン中途解約の扱い | Keyword match 67% < 80% | Define next action in weekly review issue; block; Route this case for manual review before approving the update |

## 6. ケース別結果
| Case ID | Name | Severity | Decision | Pass/Fail | Fail Reason |
|---------|------|----------|----------|-----------|-------------|
| customer_support_faq_001 | キャンペーン商品の返金条件 | S1 | ng | fail | Keyword match 33% < 80% |
| customer_support_faq_006 | 無料トライアル解約の締切 | S1 | ng | fail | Keyword match 0% < 80% |
| customer_support_faq_007 | 年額プラン中途解約の扱い | S1 | ng | fail | Keyword match 67% < 80% |
| customer_support_faq_004 | チャージバックと返金審査の関係 | S2 | ng | fail | Keyword match 0% < 50% |
| customer_support_faq_011 | 年額割引の案内条件 | S2 | ng | fail | Keyword match 0% < 50% |
| customer_support_faq_016 | 契約変更の反映条件 | S2 | ng | fail | Keyword match 33% < 50% |
| customer_support_faq_005 | 月額プランの解約反映タイミング | S2 | ok | pass | - |
| customer_support_faq_010 | 料金ページの表示場所 | S2 | ok | pass | - |
| customer_support_faq_014 | 自動更新通知の送信時期 | S2 | ok | pass | - |

## 7. 推奨アクション
- Define next action in weekly review issue
- block
- Route this case for manual review before approving the update
- allow_with_warning

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
- Overall pass rate: 33.3%
- Main failure category: synthesis (6 cases)
- Recommended next action: Define next action in weekly review issue

- Aggregation Policy: latest_run

### Recent History Summary
- Latest status: FAIL (ce7d3eb4-63a)
- Current streak: FAIL x1
- Overall pass rate trend: 33.3% -> 33.3% (0.0 pts)
- S1 pass rate trend: 0.0% -> 0.0% (0.0 pts)
- Failure action coverage (last 1): 0/1 categories (0.0%)
- Uncovered categories: synthesis (6 cases)
- Judge reliability: HIGH
- Needs human review: NO

| Metric | Actual | Threshold | Status |
|--------|--------|-----------|--------|
| S1 pass rate | 0.0% | 100.0% | NG |
| Overall pass rate | 33.3% | 85.0% | NG |
| Avg evidence recall | 100.0% | 70.0% | OK |
| Fresh case review rate | 100.0% | 80.0% | OK |

### Observed Metrics
| Metric | Average | Scored Runs |
|--------|---------|-------------|
| Avg faithfulness | 73.2% | 9 |
| Avg judge relevance | 65.0% | 9 |
| Avg evidence recall | 100.0% | 9 |

### Reliability
- Judge reliability: HIGH
- Judge fallback count: 0
- Embedding fallback: NO
- Retrieval reliability: HIGH
- Needs human review: NO

### Case Staleness
- Fresh review rate: 100.0% (9/9) within 45 days
- No stale active cases detected.

### Per-case Failures
| Case | Actual | Threshold | Name |
|------|--------|-----------|------|
| case:customer_support_faq_001 | 0.0% | 100.0% | キャンペーン商品の返金条件 |
| case:customer_support_faq_004 | 0.0% | 85.0% | チャージバックと返金審査の関係 |
| case:customer_support_faq_006 | 0.0% | 100.0% | 無料トライアル解約の締切 |
| case:customer_support_faq_007 | 0.0% | 100.0% | 年額プラン中途解約の扱い |
| case:customer_support_faq_011 | 0.0% | 85.0% | 年額割引の案内条件 |
| case:customer_support_faq_016 | 0.0% | 85.0% | 契約変更の反映条件 |

### Failure Categories
| Category | Count |
|----------|-------|
| synthesis | 6 |

### Next Actions
| Failure Category | Affected Cases | Next Action | Owner | Due |
|------------------|----------------|-------------|-------|-----|
| synthesis | customer_support_faq_001, customer_support_faq_004, customer_support_faq_006, customer_support_faq_007, customer_support_faq_011, customer_support_faq_016 | Define next action in weekly review issue | T.B.D. | T.B.D. |
