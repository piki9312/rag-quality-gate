# Proof Gate Customer Support PoC

Proof Gate is scoped to customer-facing FAQ RAG quality assurance for this PoC.
It is not a general observability platform. The demo goal is to show that a
support AI update can be checked, blocked, reviewed, reported, and explained
without asking the audience to inspect raw GitHub artifacts.

## Fastest Sales Demo

Use the deterministic demo artifacts when you need a stable screen-share flow.
They contain one pass run, one business-risk block, and one reliability-driven
human-review run.

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python scripts\create_customer_support_demo_artifacts.py
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir packs\customer_support_pack\reports\demo_runs --port 8012
```

Open these routes:

- `http://127.0.0.1:8012/packs`
- `http://127.0.0.1:8012/runs`
- `http://127.0.0.1:8012/runs/csp-pass-202604`
- `http://127.0.0.1:8012/runs/csp-block-refund-202604`
- `http://127.0.0.1:8012/runs/csp-needs-review-fallback-202604`
- `http://127.0.0.1:8012/cases/failures`
- `http://127.0.0.1:8012/reports/monthly`

## Repository Layout For The PoC

For this repository, responsibilities are split like this:

- `src/rqg/`: Proof Gate core CLI and evaluation logic.
- `packs/customer_support_pack/`: reusable customer support quality pack.
- `demos/customer_support_faq_change/`: FAQ v1 -> v2 change-accident demo assets, source FAQs, runnable cases, summaries, and before / after reports.
- `docs/user-guide/`: operator-facing runbooks, including this PoC guide.
- `docs/sales/`: proposal and sales-facing talk tracks.

The minimal before / after sales demo lives under `demos/customer_support_faq_change/`.

## FAQ Change Demo

Use the curated FAQ change demo when you want to show one compact story:

1. stale FAQ v1 returns a dangerous old-condition answer
2. Proof Gate detects an S1 failure and returns NG
3. FAQ v2 reference run removes the risky answer
4. re-gate confirms the improvement

Run from the repository root:

```powershell
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

Main files:

- `demos/customer_support_faq_change/demo_faq_v1.md`
- `demos/customer_support_faq_change/demo_faq_v2.md`
- `demos/customer_support_faq_change/generated_cases.csv`
- `demos/customer_support_faq_change/cases.csv`
- `demos/customer_support_faq_change/case_set_summary.json`
- `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- `demos/customer_support_faq_change/demo_summary.json`

When presenting, first show `1. 本番反映判定`, then `5. S1重大失敗一覧`, then `8. 月額Monitorで継続確認すべき項目` in the before report. After that, open the after report and show that the same selected cases now clear S1 and pass the gate.

## Talk Track

1. Start at `/packs` and introduce `Customer Support AI Quality Pack` as the
   reusable template for refund, cancellation, pricing, contract, deadline, and
   eligibility risk.
2. Open `/runs/csp-pass-202604` and show the clean baseline: `policy_status=pass`,
   S1 fail count `0`, judge reliability `high`, and no fallback.
3. Open `/runs/csp-block-refund-202604` and show the release stop: legacy
   `status=fail`, `policy_status=block`, S1 failures, reasons, affected case IDs,
   and next action.
4. Open `/runs/csp-needs-review-fallback-202604` and show evaluator uncertainty:
   legacy `status=pass`, but `policy_status=needs_human_review`,
   `judge_reliability=low`, fallback used, and approval pending.
5. Open `/cases/failures` to show that product owners can see the affected cases
   and recommended actions without reading JSON.
6. Open `/reports/monthly` to explain the monthly value: runs checked, blocked
   updates, S1 incidents, fallback trend, unresolved issues, and recommended
   actions.

## Reliability Contract

The legacy `status` field remains `pass`, `warn`, or `fail`. Proof Gate adds `policy_status` for business decisions:

- `pass`: safe to continue.
- `warn`: hard thresholds passed, but follow-up is recommended.
- `block`: an S1 or hard gate failure should stop release.
- `needs_human_review`: reliability degraded or uncertainty requires manual approval.

Gate artifacts include `judge_reliability`, `fallback_summary`, `retrieval_reliability`, `needs_human_review`, and an `approval` stub for future approval workflows.

Use these two demo runs to explain the difference between confirmed business
risk and Proof Gate uncertainty:

- `csp-block-refund-202604`: `policy_status=block`,
  `fallback_summary.block_origin=business_risk`, `judge_reliability=high`.
  The update is stopped because the customer-facing answer is wrong for S1
  refund/cancellation cases.
- `csp-needs-review-fallback-202604`: `policy_status=needs_human_review`,
  `fallback_summary.block_origin=evaluator_reliability`,
  `judge_reliability=low`. The answer is not treated as safely releasable
  because the evaluator fell back.

The key message is: Proof Gate blocks confirmed S1 business risk, and routes
uncertain evaluator runs to human review instead of silently passing them.

## Live Gate Option

After the screen-share demo, you can run the pack against the normal CLI flow:

```powershell
.\.venv\Scripts\python -m rqg.cli gate --pack packs\customer_support_pack --mock --log-dir runs\customer_support_pack --reset-log-dir
.\.venv\Scripts\python -m rqg.cli report-monthly --log-dir runs\customer_support_pack --month 2026-04
```

For first-run local document demos, keep Windows PowerShell in UTF-8 mode and
prefer deterministic artifacts unless the environment already has the retrieval
dependencies and embedding model available.

## Windows Notes

Run commands from the repository root in PowerShell. Use `.\.venv\Scripts\python`
to avoid PATH differences between machines. If you run the full pytest suite on
Windows and coverage/temp cleanup hits a permission error, rerun the same suite
with an explicit local `--basetemp` and `--no-cov` for functional verification:

```powershell
.\.venv\Scripts\python -m pytest --no-cov --basetemp=.pytest-tmp-full-hardening
```

## Monthly Report

Monthly artifacts are written as `monthly-summary.json` and `monthly-summary.md`. They include run volume, blocked runs, S1 incidents, top reasons, fallback trend, unresolved issues, and recommended actions.

## Pack Clone

Create a new customer-facing FAQ pack with:

```powershell
rqg init-pack packs/new_customer_support --profile customer_support
```

Then update tenant metadata, replace documents, and review S1/S2 cases before the first run.
