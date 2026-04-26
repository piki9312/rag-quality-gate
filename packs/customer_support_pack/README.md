# Customer Support AI Quality Pack

This pack is the Proof Gate PoC template for customer-facing FAQ RAG. It focuses on high-risk support answers where a wrong response can create refund, cancellation, pricing, contract, deadline, or eligibility harm.

## What It Covers

- S1: customer-facing mistakes that should block release, such as promising refunds for non-refundable digital products or giving the wrong cancellation deadline.
- S2: incomplete or ambiguous answers that should warn and create follow-up work.
- Documents: refund policy, cancellation policy, pricing FAQ, and terms summary.

## Demo Flow

1. Run `rqg gate --pack packs/customer_support_pack --mock --log-dir runs/customer_support_pack --reset-log-dir`.
2. Confirm `gate-decision.json`, `gate-report.json`, and `gate-report.md` show pass/block reasons, next actions, reliability, and fallback status.
3. Break the demo by editing `documents/refund_policy.md` or a RAG prompt so a digital product is described as refundable after download.
4. Rerun the same gate command.
5. Show that S1 failures produce `policy_status=block` or `needs_human_review`, with reasons, next actions, and reliability visible.
6. Generate monthly artifacts with `rqg report-monthly --log-dir runs/customer_support_pack --month 2026-04`.
7. Start the dashboard with `rqg serve-dashboard --workspace-dir . --port 8012` and open `/packs`, `/runs`, `/cases/failures`, and `/reports/monthly`.

## Reading Results

- `status` preserves the legacy machine contract: `pass`, `warn`, or `fail`.
- `policy_status` is the Proof Gate business decision: `pass`, `warn`, `block`, or `needs_human_review`.
- `fallback_summary` and `judge_reliability` must be checked before approving a customer-facing update.
- S1 failures should not be shipped until the failed answer and evidence are reviewed.

## Clone For Another Customer

Use `rqg init-pack packs/new_customer_support --profile customer_support --force`, then update `quality-pack.yml` tenant metadata, replace documents, and review S1/S2 cases before the first customer run.
