# Customer Support FAQ Change 2-Minute Sales Demo Script

## What This Demo Shows

This demo shows one simple customer-facing RAG failure mode.

- The FAQ changed from v1 to v2.
- The deployed RAG still answers with the old v1 rule.
- Proof Gate catches that mismatch before production promotion.
- After the FAQ is updated, the same case set passes again.

## 2-Minute Talk Track

### 0:00-0:20 Opening

Today I will show a very small example of why a RAG AI can look correct but still be unsafe to release.

In this demo, the customer support FAQ changed, but the AI is still answering from the old version. Proof Gate checks that answer set before release and decides whether it is safe to promote.

### 0:20-0:50 Before: what is happening

Open `reports/before_stale_v1/gate-report.md`.

What is happening here is simple.

- The FAQ refund and cancellation conditions were updated.
- The RAG still answers from stale v1 content.
- That means the AI can give a business-risk answer that sounds plausible but is no longer policy-correct.

Point to these sections:

- `1. 本番反映判定`: release is `NG`.
- `4. 実行結果サマリ`: `S1 pass rate` is `0.0%`, `overall pass rate` is `11.1%`.
- `5. S1重大失敗一覧`: the refund and cancellation cases are treated as critical failures.

### 0:50-1:15 What Proof Gate detected

The key point is that Proof Gate is not saying the AI failed because of tone or formatting.

It detected that the AI answered with an outdated business condition.

The representative example is this question:

- `Can I get a refund within 7 days?`

The stale answer still says standard products and campaign products are eligible, but v2 says only campaign-tagged products qualify under the normal 7-day rule.

That is why Proof Gate marks this as an S1重大失敗 and blocks production promotion.

### 1:15-1:40 After: what improved

Open `reports/after_v2_reference/gate-report.md`.

Now the same selected case set is re-run against the updated FAQ.

Point to these sections:

- `1. 本番反映判定`: now `OK`.
- `4. 実行結果サマリ`: `S1 pass rate` is `100.0%`, `overall pass rate` is `100.0%`.
- `5. S1重大失敗一覧`: the critical failures are gone.

The important message is that we did not change the demo to make it easier. We re-ran the same risky cases after the FAQ update and confirmed the improvement.

### 1:40-1:55 Why Monthly Monitor Matters

This is why monthly monitoring is necessary.

- FAQ, policy, pricing, and contract conditions keep changing.
- Prompt updates can also change answer behavior.
- A system that passed once can drift back into risky answers later.

Point to `8. 月額Monitorで継続確認すべき項目` in the before report and explain that high-risk cases should be re-run after content or prompt changes.

### 1:55-2:00 How To Explain It To The Customer

The short customer explanation is:

Your RAG may still sound fluent after a policy update, but fluent is not the same as safe. Proof Gate checks whether updated high-risk answers are still releasable before customers see them, and monthly monitoring makes sure that safety does not drift over time.

## One-Line Close

Proof Gate helps the team catch a dangerous old-answer mistake before release, fix it, and prove the recovery with the same case set.