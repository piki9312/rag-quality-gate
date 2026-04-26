# Proof Gate Customer Support PoC

Proof Gate is scoped to customer-facing FAQ RAG quality assurance for this PoC. It is not a general observability platform.

## Core Demo

1. Use `packs/customer_support_pack`.
2. Run `rqg gate --pack packs/customer_support_pack --mock --log-dir runs/customer_support_pack --reset-log-dir`.
3. Review `gate-decision.json`, `gate-report.json`, and `gate-report.md`.
4. Break a refund, cancellation, pricing, or contract answer in the RAG prompt or source document.
5. Rerun the gate and confirm S1 failures produce `policy_status=block` or `policy_status=needs_human_review`.
6. Generate monthly output with `rqg report-monthly --log-dir runs/customer_support_pack --month 2026-04`.
7. Serve the UI with `rqg serve-dashboard --workspace-dir . --port 8012`.

## Reliability Contract

The legacy `status` field remains `pass`, `warn`, or `fail`. Proof Gate adds `policy_status` for business decisions:

- `pass`: safe to continue.
- `warn`: hard thresholds passed, but follow-up is recommended.
- `block`: an S1 or hard gate failure should stop release.
- `needs_human_review`: reliability degraded or uncertainty requires manual approval.

Gate artifacts include `judge_reliability`, `fallback_summary`, `retrieval_reliability`, `needs_human_review`, and an `approval` stub for future approval workflows.

## Monthly Report

Monthly artifacts are written as `monthly-summary.json` and `monthly-summary.md`. They include run volume, blocked runs, S1 incidents, top reasons, fallback trend, unresolved issues, and recommended actions.

## Pack Clone

Create a new customer-facing FAQ pack with:

```powershell
rqg init-pack packs/new_customer_support --profile customer_support
```

Then update tenant metadata, replace documents, and review S1/S2 cases before the first run.
