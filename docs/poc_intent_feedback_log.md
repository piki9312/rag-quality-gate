# PoC Intent Feedback Log

## Purpose

This log is a lightweight template for recording feedback on Case Intent seeds
during PoC or release-gate review.

It is not a runtime artifact. It does not change `cases.csv`, GateDecision,
`gate-report.json`, or ReviewPacket.

## Feedback Log Template

| Date | Project / pack | Intent ID | Risk domain | Feedback type | Observation | Proposed action | Owner | Status |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  | missing_coverage / unclear_wording / too_broad / too_narrow / useful |  |  |  |  |

## Feedback Types

| Type | Meaning |
|---|---|
| `missing_coverage` | The intent library lacks an important S1 risk pattern |
| `unclear_wording` | The intent is hard for reviewers to interpret |
| `too_broad` | The intent covers too many customer-specific situations |
| `too_narrow` | The intent misses common variants |
| `useful` | The intent helped create or review a strong draft case |

## What To Record

Record:

- intent ID
- risk domain
- safe summary of the gap or lesson
- whether the intent helped create a `needs_review` draft
- whether a human-approved active case was eventually added to `cases.csv`
- whether the intent should be edited, split, deprecated, or expanded

Do not record:

- customer names
- customer source document text
- raw answers
- retrieved chunks
- customer-specific `expected_answer`
- customer-specific `expected_evidence`

## Follow-Up Actions

| Action | When to use |
|---|---|
| edit_intent | The intent is useful but wording should be clearer |
| split_intent | One intent covers multiple distinct S1 risks |
| add_variant | More question templates are needed |
| add_domain | A risk domain is missing |
| deprecate_intent | The intent is misleading or no longer useful |

## Review Cadence

For early PoCs, review this log after each release-gate run or customer review.

For monthly operations, review it alongside safe usage summaries and recurring
No-Go / Conditional findings.
