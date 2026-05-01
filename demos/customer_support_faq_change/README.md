# Customer Support FAQ Change Demo

## Shortest Sales Demo

If you need the 2 minute version, use this path:

1. Run the refresh command.
2. Open the before report and show the release block.
3. Open the after report and show the recovery.
4. Open the one-page comparison and close with the monthly monitoring message.

Command:

```powershell
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

Open these files in order:

- `demos/customer_support_faq_change/sales_demo_script.md`
- `demos/customer_support_faq_change/before_after_onepager.md`
- `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- `demos/customer_support_faq_change/demo_summary.json`

Where to look in the before report:

- `1. 本番反映判定`: show `NG` and `policy_status: BLOCK`.
- `4. 実行結果サマリ`: show `overall_pass_rate: 11.1%` and `s1_pass_rate: 0.0%`.
- `5. S1重大失敗一覧`: show the refund and cancellation failures.
- `8. 月額Monitorで継続確認すべき項目`: connect the demo to monthly operations.

Where to look in the after report:

- `1. 本番反映判定`: show `OK` and `policy_status: PASS`.
- `4. 実行結果サマリ`: show `overall_pass_rate: 100.0%` and `s1_pass_rate: 100.0%`.
- `5. S1重大失敗一覧`: confirm that the critical failures are gone.

What `demo_summary.json` means:

- `before`: the stale FAQ v1 run that should be blocked.
- `after`: the updated FAQ v2 reference run that should pass.
- `representative_s1_failure`: one customer-facing failure that is easy to explain in a meeting.
- `key_message`: the short business message for the close.

## Directory Layout

- `demo_faq_v1.md` / `demo_faq_v2.md`: the old and updated FAQ source documents.
- `generated_cases.csv`: curated generated cases used as the demo source-of-truth.
- `cases.csv`: the runnable case set refreshed from `generated_cases.csv`.
- `case_set_summary.json`: compact summary for the runnable demo cases.
- `reports/before_stale_v1/`: stale-v1 gate artifacts.
- `reports/after_v2_reference/`: v2 reference gate artifacts.
- `demo_summary.json`: before / after comparison for the sales walkthrough.

## What This Shows

- Before: the deployed RAG still answers from stale FAQ v1 and gives risky answers with old refund or cancellation conditions.
- Proof Gate detects those answers as S1重大失敗 and returns NG.
- After: the same selected cases are re-run against FAQ v2 and the risky answers improve.
- Re-gate confirms the improvement in one short before / after comparison.

## Run

From the repository root:

```powershell
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

Artifacts are refreshed under:

- `demos/customer_support_faq_change/generated_cases.csv`
- `demos/customer_support_faq_change/cases.csv`
- `demos/customer_support_faq_change/case_set_summary.json`
- `demos/customer_support_faq_change/reports/before_stale_v1/`
- `demos/customer_support_faq_change/reports/after_v2_reference/`
- `demos/customer_support_faq_change/demo_summary.json`

## What To Show In The Demo

1. Open `reports/before_stale_v1/gate-report.md` and point first to `1. 本番反映判定` and `5. S1重大失敗一覧`.
2. Explain that `Can I get a refund within 7 days?` is answered with the old v1 rule instead of the stricter v2 rule.
3. Open `reports/after_v2_reference/gate-report.md` and show that the same selected case set is now re-evaluated against v2 and the gate result improves.
4. Open `demo_summary.json` and compare `before` vs `after` pass rates and S1 failures.

## Sales Materials

- `sales_demo_script.md`: 2 minute spoken sales script.
- `before_after_onepager.md`: one-page before / after comparison memo.

## Reading The Reports

- Before: focus on `1. 本番反映判定`, `4. 実行結果サマリ`, and `5. S1重大失敗一覧`.
- After: focus on the same sections and show that S1 failures are removed.
- The top section is the sales-facing message. The lower `運用向け詳細` section is the follow-up proof for technical stakeholders.