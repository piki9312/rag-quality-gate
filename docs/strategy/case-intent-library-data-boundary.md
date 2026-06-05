# Case Intent Library Data Boundary

## Purpose

This document defines the data boundary for the Case Intent Library, `gen_cases`,
PatternDraft review artifacts, and approved `cases.csv` files.

Proof Gate is designed for AI vendors and SI partners. The vendor or the
vendor's customer controls customer-specific raw data. Proof Gate's reusable
asset is the abstract test design layer, not the customer's private answer key.

## Operating Assumption

The primary customer is an AI delivery vendor.

End-customer raw data should not be managed by the Proof Gate operator by
default. This includes FAQ text, policy text, inquiry logs, contract terms,
pricing details, private evidence, and customer-specific expected answers.

Proof Gate can still help vendors produce review candidates, but those
candidates remain vendor-owned or customer-controlled artifacts until reviewed.

## Why Proof Gate Does Not Own Raw Customer Data

Keeping raw customer data out of Proof Gate's core assets protects:

- customer confidentiality
- vendor delivery ownership
- partner distribution flexibility
- safe/full report separation
- Proof Gate's ability to reuse abstract quality assets across customers

The product asset should be reusable coverage and release-review logic, not a
repository of customer-specific cases.

## What The Library May Store

The Case Intent Library may store abstract, reusable assets:

| Asset | Allowed? | Notes |
| --- | --- | --- |
| `intent_id` | Yes | Stable abstract identifier. |
| `risk_domain` / `risk_category` | Yes | Example: refund, cancellation, pricing. |
| `failure_pattern_id` | Yes | Example: `FP-STALEREF-001`. |
| Abstract question template | Yes | No customer-specific text. |
| `test_design_type` | Yes | Boundary value, decision table, state transition, etc. |
| Required evidence type | Yes | Example: refund policy, contract terms. |
| Abstract required claim type | Yes | Claim class, not customer-specific wording. |
| Abstract forbidden claim type | Yes | Claim class, not customer-specific wording. |
| `release_rule_hint` | Yes | Example: block, allow_with_warning, needs_human_review. |
| Coverage Rule | Yes | Defines when an intent or active case is expected. |

## What The Library Must Not Store

The Case Intent Library must not store customer-specific raw or answer-key data:

| Asset | Allowed? | Reason |
| --- | --- | --- |
| Customer name | No | Customer-specific metadata. |
| Customer FAQ body | No | Raw customer document. |
| Inquiry log text | No | Private operational data. |
| Personal information | No | Protected data. |
| Contract terms verbatim | No | Customer-specific legal/business text. |
| Concrete pricing amounts | No | Customer-specific commercial terms. |
| Customer-specific `expected_answer` | No | Vendor/customer correctness boundary. |
| Customer-specific `required_claims` | No | Customer-specific answer key. |
| Customer-specific `forbidden_claims` | No | Customer-specific answer key. |
| Customer source document body | No | Full/private evidence. |

## Case Intent vs Customer Case

A Case Intent is an abstract quality-design asset.

Example:

```text
intent_id: refund_mid_contract_cancellation
risk_domain: refund
test_design_type: decision_table
required_evidence_type: refund_policy
abstract_required_claim_type: refund_eligibility
release_rule_hint: needs_human_review
```

A customer case is a vendor/customer-controlled artifact.

Example:

```text
question: Customer-specific question text
expected_answer: Customer-approved answer
expected_evidence: Customer document reference
status: active
```

The first can be a Proof Gate asset. The second should remain under vendor or
customer control.

## gen_cases / PatternDraft Responsibility

`gen_cases` and PatternDraft can:

- match abstract intents to customer document sections
- propose review candidates when evidence can be found
- mark generated answers as unapproved drafts
- emit `status=needs_review` review artifacts

They must not:

- auto-create `status=active` cases
- guarantee customer-specific correctness
- convert generated `expected_answer` into a formal answer key
- require raw customer data to be sent to the Proof Gate operator

## Review Artifact Boundary

The following are review artifacts, not formal release evidence:

- old `review.csv`
- PatternDraft `pattern-draft-review.csv`
- `review_cases.yaml`
- `review_cases.md`

These artifacts are vendor-owned or customer-controlled. They may contain
customer-specific draft answers or evidence references, so they should not be
treated as Proof Gate operator-owned data.

`review_cases.md` is only a preview. `review_cases.yaml` is the machine-readable
source for `approve-cases`.

## Active cases.csv Boundary

Only a formal `cases.csv` row with `status=active` is approved-for-run.

```text
Case Intent Library
  -> gen_cases / PatternDraft
  -> review artifact
  -> vendor/customer review
  -> active cases.csv
  -> Gate execution
```

`needs_review`, `draft`, and `deprecated` rows are not Gate execution targets.

## Safe Summary Boundary

Proof Gate-side improvement should use safe summaries where possible:

- category
- severity
- failure pattern id
- intent id
- coverage status
- review status
- aggregate counts

It should not require:

- raw question
- raw answer
- raw evidence
- customer document text
- source path with private customer context
- owner or personal metadata

## Implementation Notes

This document is a boundary contract. It does not require changes to the formal
`cases.csv` columns, `EvalCase`, `QATestCase`, GateDecision, report JSON, or CI
templates.

Future validator work should start with warnings. Unknown markers should not be
errors unless a later migration plan explicitly changes that contract.
