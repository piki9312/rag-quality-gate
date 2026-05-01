# Customer Support FAQ Change Before / After One-Pager

## What This Page Is For

Use this page when you need one screen that summarizes the business outcome of the demo.

## Before / After Summary

| 項目 | Before: stale v1 | After: v2 reference |
|---|---:|---:|
| 本番反映判定 | NG | OK |
| policy_status | BLOCK | PASS |
| S1 pass rate | 0.0% | 100.0% |
| overall pass rate | 11.1% | 100.0% |
| S1 failures | 3 | 0 |
| 代表S1重大失敗 | customer_support_faq_001: 7日以内返金を旧ルールで許容 | 解消 |
| 顧客向け一言コメント | 古いFAQ条件のままでも自然に答えてしまうため、本番前ブロックが必要 | 更新後の回答は新ルールに沿っており、再判定でも通過 |

## Representative S1 Failure

- Case ID: `customer_support_faq_001`
- Question: `Can I get a refund within 7 days?`
- Fail reason: `Keyword match 33% < 80%`
- Business meaning: the AI answered with the old v1 refund rule and treated standard products as refundable under the normal 7-day policy.

## Customer-Facing Message

Before:

The AI still sounds confident, but it is using an outdated refund condition, so releasing it would create customer-facing policy risk.

After:

Once the FAQ update is reflected and re-checked with the same high-risk case set, the critical failures disappear and the release decision becomes explainably safe.

## Files To Open During The Demo

- `reports/before_stale_v1/gate-report.md`
- `reports/after_v2_reference/gate-report.md`
- `demo_summary.json`
- `sales_demo_script.md`