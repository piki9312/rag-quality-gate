# Case Intent Draft Examples

This document is non-runtime.
It does not define active cases.
It does not replace formal cases.csv.
It only demonstrates how Case Intents can be manually translated into
needs_review draft candidates.

Runtime flow remains:

```text
Case Intent Library
-> needs_review draft candidate
-> human review
-> active formal cases.csv
-> validate-pack
-> eval
-> gate
-> ReviewPacket
```

この文書はruntime入力ではない。
active cases.csvの代替ではない。
Case Intentからneeds_review候補へ落とす検証例である。

## Purpose

This document validates the new S1 Case Intent Library seed against one existing
demo pack by manually deriving sample `needs_review` case drafts.

It does not change `cases.csv`, GateDecision, ReviewPacket, `gate-report.json`,
or any CLI behavior.

## Pack Used

| Item | Value |
|---|---|
| Pack | `packs/release_review_demo` |
| Pack type | fictional release review demo pack |
| Existing runtime source of truth | `packs/release_review_demo/cases.csv` |
| Change event | `packs/release_review_demo/change-event.yml` |
| Affected categories | `pricing`, `refund`, `cancellation` |
| Synthetic source documents | `refund_policy.md`, `pricing_policy.md`, `cancellation_policy.md` |

The demo pack is fictional and safe for documentation examples. The examples
below use safe summaries and document references rather than customer raw data,
full retrieved chunks, or real customer-specific expected answers.

## Runtime Boundary

The Case Intent Library remains non-runtime.

```text
Case Intent Library
  -> needs_review draft candidate
  -> human review
  -> active formal cases.csv
  -> validate-pack
  -> eval
  -> gate
  -> ReviewPacket
```

Only active rows in formal `cases.csv` are runtime evidence. The sample drafts
below must not be executed by `rqg gate` unless a human reviewer approves them
and intentionally adds them to active `cases.csv`.

## Selected Intents

The selected intents are the most relevant to the demo pack's affected
categories and existing release review story:

| Intent ID | Risk domain | Why selected |
|---|---|---|
| `s1_refund_policy_reversal` | `refund_cancellation` | Existing demo cases cover refund reversal and refund eligibility confusion. |
| `s1_cancellation_fee_omission` | `refund_cancellation` | Cancellation handling can miss required fee, term, or confirmation conditions. |
| `s1_stale_pricing_reference` | `pricing_billing` | The demo pack models stale pricing / old policy references after document update. |
| `s1_billing_exception_overpromise` | `pricing_billing` | Campaign or billing exception answers can overpromise unsupported handling. |
| `s1_deadline_miscalculation` | `deadline_procedure` | The demo pack includes old cancellation deadline behavior. |
| `s1_required_procedure_omission` | `deadline_procedure` | Cancellation and refund flows depend on required procedure steps and owner review. |

## Draft Examples

### 1. Refund Rule Reversal

| Field | Draft value |
|---|---|
| selected intent_id | `s1_refund_policy_reversal` |
| risk_domain | `refund_cancellation` |
| failure_pattern | `refund_rule_reversal` |
| why this intent applies | `packs/release_review_demo/cases.csv` already contains S1 refund cases where refund availability can be reversed or confused across plan conditions. |
| sample question | If a user cancels a paid plan after use has started, can the assistant say a refund is available? |
| expected_answer placeholder | `needs_review`: State the approved refund condition for the applicable plan and route exception or unclear cases to human review. |
| expected_evidence placeholder | `packs/release_review_demo/documents/refund_policy.md#refund-rules` |
| block_reason | Refund answer may reverse the applicable refund rule or skip required human review. |
| required human review checks | Confirm current refund source document, effective date, plan-specific expected answer, exception handling owner, and notes markers. |
| active or needs_review | Remain `needs_review`; placeholder expected answer/evidence cannot become active. |
| additional confirmation before active | Human reviewer must approve the demo/customer-specific expected answer, source section, effective date, escalation owner, and `answer_status:vendor-approved` marker before adding this to active `cases.csv`. |

Recommended notes markers:

```text
intent:s1_refund_policy_reversal; pattern:refund_rule_reversal; design:risk_based; release:block; answer_status:unapproved-draft
```

### 2. Cancellation Fee / Condition Omission

| Field | Draft value |
|---|---|
| selected intent_id | `s1_cancellation_fee_omission` |
| risk_domain | `refund_cancellation` |
| failure_pattern | `fee_or_penalty_omission` |
| why this intent applies | The demo pack includes cancellation policy changes. A draft case should check whether the assistant omits minimum term, fee, or required confirmation conditions. |
| sample question | Can a customer cancel immediately without any additional fee or confirmation step? |
| expected_answer placeholder | `needs_review`: Explain only the approved cancellation conditions and mention required confirmation when the policy requires it. |
| expected_evidence placeholder | `packs/release_review_demo/documents/cancellation_policy.md#cancellation-conditions` |
| block_reason | Cancellation answer may omit fee, minimum term, or confirmation requirements. |
| required human review checks | Confirm whether fee/minimum-term conditions exist in the current demo policy, confirm expected wording, and assign escalation owner. |
| active or needs_review | Remain `needs_review`; the demo pack's active `cases.csv` is unchanged. |
| additional confirmation before active | Human reviewer must confirm whether the policy actually contains fee/minimum-term conditions, approve the expected answer, approve evidence, and explicitly promote the row through the normal review flow. |

Recommended notes markers:

```text
intent:s1_cancellation_fee_omission; pattern:fee_or_penalty_omission; design:decision_table; release:block; answer_status:unapproved-draft
```

### 3. Stale Pricing Reference

| Field | Draft value |
|---|---|
| selected intent_id | `s1_stale_pricing_reference` |
| risk_domain | `pricing_billing` |
| failure_pattern | `stale_reference` |
| why this intent applies | `change-event.yml` says pricing documents changed, and the pack story includes stale pricing / old policy reference risk. |
| sample question | Does the old campaign price still apply to the current plan? |
| expected_answer placeholder | `needs_review`: Use only the current pricing source and route uncertainty about campaign terms to the pricing owner. |
| expected_evidence placeholder | `packs/release_review_demo/documents/pricing_policy.md#current-pricing` |
| block_reason | Pricing answer may rely on stale pricing or unsupported campaign terms. |
| required human review checks | Confirm current pricing document, effective date, campaign term status, pricing owner, and expected answer wording. |
| active or needs_review | Remain `needs_review` until pricing owner approval. |
| additional confirmation before active | Pricing owner must verify the current pricing source, campaign status, approved wording, source section, and review status before active `cases.csv` inclusion. |

Recommended notes markers:

```text
intent:s1_stale_pricing_reference; pattern:stale_reference; design:stale_reference; release:block; answer_status:unapproved-draft
```

### 4. Billing / Campaign Exception Overpromise

| Field | Draft value |
|---|---|
| selected intent_id | `s1_billing_exception_overpromise` |
| risk_domain | `pricing_billing` |
| failure_pattern | `unsupported_exception_commitment` |
| why this intent applies | Existing demo rows include campaign-related generalization. A draft case should check that the assistant does not promise billing or campaign exceptions without source support. |
| sample question | Can the assistant tell a customer that a special campaign exception will be applied to their bill? |
| expected_answer placeholder | `needs_review`: Do not promise an exception; explain that campaign or billing exceptions require confirmation by the responsible owner. |
| expected_evidence placeholder | `packs/release_review_demo/documents/pricing_policy.md#campaign-terms` |
| block_reason | Billing answer may promise an exception without approved source support. |
| required human review checks | Confirm campaign policy source, exception owner, escalation path, and whether the expected answer should be active. |
| active or needs_review | Remain `needs_review`; do not auto-promote from intent. |
| additional confirmation before active | Human reviewer must verify that the demo policy supports the exception handling statement, approve escalation wording, and remove the unapproved-draft status through the review flow. |

Recommended notes markers:

```text
intent:s1_billing_exception_overpromise; pattern:unsupported_exception_commitment; design:risk_based; release:block; answer_status:unapproved-draft
```

### 5. Cancellation Deadline Miscalculation

| Field | Draft value |
|---|---|
| selected intent_id | `s1_deadline_miscalculation` |
| risk_domain | `deadline_procedure` |
| failure_pattern | `deadline_miscalculation` |
| why this intent applies | The demo pack contains cancellation deadline cases and a change event tied to cancellation rule changes. |
| sample question | By when must a customer submit a cancellation request to stop the next renewal? |
| expected_answer placeholder | `needs_review`: State the current approved deadline condition and avoid using old notice periods. |
| expected_evidence placeholder | `packs/release_review_demo/documents/cancellation_policy.md#deadline-policy` |
| block_reason | Deadline answer may misstate timing or skip required condition checks. |
| required human review checks | Confirm current deadline policy, effective date, renewal timing assumptions, expected answer wording, and escalation owner. |
| active or needs_review | Remain `needs_review` until deadline owner approval. |
| additional confirmation before active | Deadline owner must approve the exact deadline rule, assumptions, evidence section, and expected answer before the case can be copied into active `cases.csv`. |

Recommended notes markers:

```text
intent:s1_deadline_miscalculation; pattern:deadline_miscalculation; design:state_transition; release:block; answer_status:unapproved-draft
```

### 6. Required Procedure Omission

| Field | Draft value |
|---|---|
| selected intent_id | `s1_required_procedure_omission` |
| risk_domain | `deadline_procedure` |
| failure_pattern | `required_procedure_omission` |
| why this intent applies | Refund and cancellation flows may require a request, confirmation, or owner review before the assistant can guide release-sensitive handling. |
| sample question | Can the assistant tell the user to proceed with cancellation without submitting the required request or confirmation? |
| expected_answer placeholder | `needs_review`: Include the required request or confirmation step and route missing information to the responsible owner. |
| expected_evidence placeholder | `packs/release_review_demo/documents/cancellation_policy.md#required-procedure` |
| block_reason | Procedure answer may omit mandatory steps or required approvals. |
| required human review checks | Confirm required procedure source, form or request reference, owner approval condition, and expected answer wording. |
| active or needs_review | Remain `needs_review`; active `cases.csv` is not modified by this example. |
| additional confirmation before active | Human reviewer must confirm the required steps/forms/approval owner and approve the customer/demo-specific answer and evidence before promotion to active. |

Recommended notes markers:

```text
intent:s1_required_procedure_omission; pattern:required_procedure_omission; design:decision_table; release:block; answer_status:unapproved-draft
```

## Validation Notes

This manual mapping confirms that the seed library can support practical
release-gate draft design for an existing demo pack without becoming a runtime
source.

The useful pattern is:

- select affected categories from `change-event.yml`
- pick relevant S1 intents
- create `needs_review` draft candidates
- have a human approve demo/customer-specific expected answer and evidence
- add only approved rows to active formal `cases.csv`
- run `validate-pack`, `eval`, and `gate`

## Non-Goals

This document does not:

- implement `draft-cases`
- modify `packs/release_review_demo/cases.csv`
- create executable cases
- change formal `cases.csv` schema
- change GateDecision
- change ReviewPacket
- change `gate-report.json`
- store real customer-specific expected answers or evidence in the common library
