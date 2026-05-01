# Proof Gate 実行レポート

## 1. 本番反映判定
- 判定: OK
- policy_status: PASS
- summary: OK。現在の閾値では本番反映可能です。

## 2. 実行概要
- client_name: demo_customer
- app_name: Customer Support AI Quality Pack
- run_id: 36d43c04-53a
- current_cases: 9
- baseline_runs: 0
- aggregation_policy: latest_run
- needs_human_review: NO
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
| customer_support_faq_001 | Campaign refund window | S1 | ok | pass | - |
| customer_support_faq_006 | Free-trial cancellation | S1 | ok | pass | - |
| customer_support_faq_007 | Mid-term annual cancellation | S1 | ok | pass | - |
| customer_support_faq_004 | Chargeback and refund overlap | S2 | ok | pass | - |
| customer_support_faq_005 | Monthly cancellation timing | S2 | ok | pass | - |
| customer_support_faq_010 | Plan price display | S2 | ok | pass | - |
| customer_support_faq_011 | Annual discount disclosure | S2 | ok | pass | - |
| customer_support_faq_014 | Auto-renewal notice | S2 | ok | pass | - |
| customer_support_faq_016 | Contract amendment timing | S2 | ok | pass | - |

## 7. 推奨アクション
- 現時点で追加対応は不要です。

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
- Policy status: PASS
- S1 pass rate: 100.0% (0 S1 failures)
- Overall pass rate: 100.0%
- Main failure category: None
- Recommended next action: No immediate action required.

- Aggregation Policy: latest_run

### Recent History Summary
- Latest status: PASS (36d43c04-53a)
- Current streak: PASS x1
- Overall pass rate trend: 100.0% -> 100.0% (0.0 pts)
- S1 pass rate trend: 100.0% -> 100.0% (0.0 pts)
- Judge reliability: HIGH
- Needs human review: NO

| Metric | Actual | Threshold | Status |
|--------|--------|-----------|--------|
| S1 pass rate | 100.0% | 100.0% | OK |
| Overall pass rate | 100.0% | 85.0% | OK |
| Avg evidence recall | 100.0% | 70.0% | OK |
| Fresh case review rate | 100.0% | 80.0% | OK |

### Observed Metrics
| Metric | Average | Scored Runs |
|--------|---------|-------------|
| Avg faithfulness | 66.6% | 9 |
| Avg judge relevance | 49.2% | 9 |
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
