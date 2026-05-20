# Review Stages and Customer Reports

Proof Gate has two different operating contexts. They use the same Gate, ReviewPacket, dashboard, and safe/full evidence boundary, but the business meaning is different.

## Pre-Delivery Quality Review

Use `pre_delivery` when a vendor or implementation team is checking whether a RAG or business AI is ready to deliver.

Typical questions:

- Is this AI answer workflow good enough to deliver?
- Are unresolved S1/S2 blockers still present?
- Can the vendor explain the quality status to the customer?
- Is a customer-facing diagnostic report safe and appropriate to share?

In this stage, `change-event.yml` is optional. It is normal for an initial diagnostic or pre-delivery review to have no explicit change event.

Suggested customer-facing report names:

- AI Answer Quality Diagnostic Report
- Pre-Delivery Quality Review
- RAG Pre-Delivery Quality Review

## Post-Delivery Change Review

Use `post_delivery_change` after the AI has been delivered and a FAQ, policy, pricing table, prompt, model, retriever, chunking, embedding, or config change may affect answers.

Typical questions:

- What changed?
- Did the change introduce answer quality regression?
- Is it safe to release the changed AI behavior?
- What evidence and decision record remain after review?

In this stage, `change-event.yml` is central. It should describe the change with bounded metadata such as change type, version, hash, category, affected document count, and retest reason. Avoid customer names, raw document names, internal paths, sensitive release names, or customer-specific summaries.

Suggested customer-facing report names:

- Change Impact Quality Review
- Post-Delivery Change Review
- Release Review Report

## Monthly Review

Use `monthly_review` for recurring maintenance or support-contract reporting. It may summarize multiple changes, residual risks, reruns, or quality trends.

Suggested customer-facing report names:

- Monthly Quality Review
- Monthly AI Answer Quality Report

## Shareability vs Submission Readiness

Proof Gate keeps two separate concepts:

| Concept | Meaning | Example |
|---|---|---|
| `customer_shareability` | Whether the artifact is safe to share as information. It checks that raw question, answer, evidence, source path, owner, and full metadata are not exposed. | A safe No-Go draft can be `shareable`. |
| `customer_submission_readiness` | Whether the artifact is recommended as a formal customer submission. It considers Go/No-Go, unresolved S1/S2, ProductionReadiness, and PM approval. | A No-Go report is usually `not_recommended` even if it is safe to share. |

For No-Go runs, do not present the output as a formal customer report by default. Use the dashboard for internal remediation. Share a safe draft only when the PoC agreement requires interim disclosure or when the customer must see document-side issues.

## Dashboard Boundary

The read-only dashboard is an internal vendor review aid. It is not the customer-facing delivery artifact.

Use the dashboard to inspect:

- Delivery Review Summary
- S1/S2 Blocking List
- Major Failures
- Failure Detail
- Production Readiness
- Document Corpus
- Change Event Card

Use the customer review export for safe sharing. Full details remain local, private runner, or customer-controlled only.

## ReleaseDecision Boundary

ReleaseDecision is not a customer report. It is the vendor-side decision record that states who approved, rejected, deferred, or conditionally accepted a delivery or release.

Recommended flow:

1. Run the Gate.
2. Review the dashboard internally.
3. Fix unresolved blockers and rerun if needed.
4. For Go or Conditional results, generate the customer-facing report.
5. Record the PM decision as ReleaseDecision.

Proof Gate does not guarantee all AI answers are correct. It supports quality review and release judgment for the configured cases, documents, and evidence policy.
