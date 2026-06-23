# Diagnostic PoC Customer Inputs

## Purpose

This document explains what an AI vendor or customer should prepare for a
`RAG/FAQ Bot Pre-Release Diagnostic PoC`.

The goal is to collect enough material to review high-risk answers without
turning Proof Gate into a repository for customer raw data.

## Required Inputs

| Input | Why it is needed | Boundary |
|---|---|---|
| FAQ / help center content | Defines common answer scope. | Use customer-approved or sanitized copy. |
| Terms, rules, or policy documents | Provides evidence for high-risk answers. | Keep full documents in customer-controlled or private working area. |
| Pricing table or billing policy | Supports pricing and billing S1/S2 cases. | Avoid putting real pricing into shared common libraries. |
| Cancellation / refund conditions | Supports high-risk release gate cases. | Treat as customer-specific expected behavior. |
| Support policy / escalation flow | Defines when the assistant must route to a human. | Do not hard-code customer owners in shared assets. |
| Expected risky questions | Helps prioritize S1/S2 review. | Can be sanitized or paraphrased. |
| Existing bot sample answers | Useful for diagnosis when available. | Treat raw answer logs as private/full data. |
| Change history | Defines what changed before release. | Prefer bounded `change-event.yml` metadata. |
| Intended production or release decision point | Clarifies whether this is pre-delivery, post-change, or monthly review. | Use bounded release labels, not sensitive internal project names. |

## Optional Inputs

- Past incident examples.
- Customer-facing report format preferences.
- Internal review criteria.
- Existing RAG endpoint or staging API contract.
- Known failure categories or customer complaints.
- Redacted logs or sampled answers.

## Inputs To Avoid

Do not collect these unless the environment and agreement explicitly allow it:

- Unnecessary personal data.
- Raw inquiry logs that are not needed for the PoC.
- Full contract text with sensitive clauses when a sanitized excerpt is enough.
- Legal judgment requests that should be handled by legal/domain owners.
- Unmasked API keys, credentials, or customer secrets.
- Customer documents intended to become shared Proof Gate assets.

## Data Boundary

Shared Proof Gate assets may contain abstract review design:

- Case Intent IDs.
- Failure patterns.
- Claim templates.
- Test design types.
- Evidence requirement types.
- Release rule hints.

Shared Proof Gate assets must not contain:

- Customer names.
- Customer-specific FAQ or policy text.
- Raw answer logs.
- Retrieved chunks.
- Customer-specific expected answers.
- Customer-specific expected evidence.
- Private source document text.

Customer-specific material belongs in the vendor/customer pack or private
working environment. Active formal `cases.csv` is the runtime source of truth
for execution.

## Customer-Safe Report Expectations

The customer-facing output should normally be a safe or redacted review package:

- release decision signal;
- S1/S2 risk summary;
- evidence status summary;
- recommended remediation;
- residual risk notes;
- next review proposal.

Full raw evidence should stay in local, private, or customer-controlled storage
unless the customer explicitly approves sharing.
