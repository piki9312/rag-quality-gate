# Customer Support FAQ Change Demo Draft

## Purpose

Use this draft when pitching the Proof Gate PoC for customer-facing FAQ RAG.

The message is simple:

1. FAQ conditions change over time.
2. A deployed RAG can keep answering with the old condition.
3. That creates a customer-facing business-risk answer.
4. Proof Gate detects the risk before release and shows a readable correction path.

## Demo Assets

- Demo root: `demos/customer_support_faq_change/`
- Before report: `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- After report: `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- Comparison summary: `demos/customer_support_faq_change/demo_summary.json`

## Talk Track

### Before

- Open the stale-v1 report.
- Start at `1. 本番反映判定` and show that the release decision is NG.
- Move to `5. S1重大失敗一覧` and point at the refund case asking whether a refund is available within 7 days.
- Explain that the AI still answered from the old rule and missed the new campaign-only condition.

### After

- Open the v2 reference report.
- Show that `1. 本番反映判定` changed to OK.
- Show that `5. S1重大失敗一覧` is empty.
- Explain that the same selected cases were re-run against the updated FAQ and the risky answer no longer passed through.

### Close

- Open `demo_summary.json`.
- Compare before vs after S1 pass rate, total pass rate, and S1 failure count.
- Close with: Proof Gate does not replace the RAG. It verifies that a changed RAG answer is still safe to release.

## Suggested One-Line Message

Proof Gate lets the team show a dangerous FAQ change accident, block it as an S1 failure, fix the content, and prove the improvement in one repeatable demo.