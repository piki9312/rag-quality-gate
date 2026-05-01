# Customer Support AI Quality Pack

This pack is the Proof Gate PoC template for customer-facing FAQ RAG. It focuses on high-risk support answers where a wrong response can create refund, cancellation, pricing, contract, deadline, or eligibility harm.

## What It Covers

- S1: customer-facing mistakes that should block release, such as promising refunds for non-refundable digital products or giving the wrong cancellation deadline.
- S2: incomplete or ambiguous answers that should warn and create follow-up work.
- Documents: refund policy, cancellation policy, pricing FAQ, and terms summary.

## Demo Flow

For a stable PoC screen share, create the deterministic demo artifacts first:

```powershell
.\.venv\Scripts\python scripts\create_customer_support_demo_artifacts.py
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir packs\customer_support_pack\reports\demo_runs --port 8012
```

Then show these runs:

1. `csp-pass-202604`: clean baseline, `policy_status=pass`, no fallback.
2. `csp-block-refund-202604`: confirmed S1 business risk, `policy_status=block`, `fallback_summary.block_origin=business_risk`.
3. `csp-needs-review-fallback-202604`: evaluator uncertainty, `policy_status=needs_human_review`, `judge_reliability=low`, `fallback_summary.block_origin=evaluator_reliability`.

Open `/packs`, `/runs`, `/cases/failures`, and `/reports/monthly` to explain the pack, latest runs, failed cases, and monthly operating value.

For a live follow-up, run `rqg gate --pack packs/customer_support_pack --mock --log-dir runs/customer_support_pack --reset-log-dir`, then `rqg report-monthly --log-dir runs/customer_support_pack --month 2026-04`.

## Reading Results

- `status` preserves the legacy machine contract: `pass`, `warn`, or `fail`.
- `policy_status` is the Proof Gate business decision: `pass`, `warn`, `block`, or `needs_human_review`.
- `fallback_summary` and `judge_reliability` must be checked before approving a customer-facing update.
- S1 failures should not be shipped until the failed answer and evidence are reviewed.
- A business-risk block means the evaluator was reliable and the answer violated an S1 case.
- A fallback-driven review means Proof Gate could not confidently certify the run, so the update needs human review before release.

## Clone For Another Customer

Use `rqg init-pack packs/new_customer_support --profile customer_support --force`, then update `quality-pack.yml` tenant metadata, replace documents, and review S1/S2 cases before the first customer run.
