# S1 Human Review Checklist

## Purpose

This checklist defines the minimum human review expected before an S1 Case
Intent becomes an active formal case.

It is a review aid. It does not make Case Intent Library entries executable.

## Runtime Rule

Only active formal `cases.csv` rows are executed by Proof Gate.

S1 intents and generated draft candidates must remain review material until a
human reviewer approves customer-specific fields and enters the case into
active `cases.csv`.

## Required Review Fields

| Field | Review question | Required before active? |
|---|---|---|
| `case_id` | Is the case ID stable and unique in the customer pack? | yes |
| `status` | Is the status intentionally set to `active` after approval? | yes |
| `severity` | Is S1 appropriate for this customer risk? | yes |
| `category` | Does the category match the customer business risk? | yes |
| `question` | Is the question customer-appropriate and free of raw private data? | yes |
| `expected_answer` | Has the customer/vendor reviewer approved the expected answer? | yes |
| `expected_evidence` | Is the evidence reference customer-approved and specific enough? | yes |
| `eval_mode` | Is the evaluation mode appropriate for the risk? | yes |
| `source_doc` | Does the source reference point to the approved source of truth? | yes |
| `owner` | Is the review or escalation owner clear? | yes |
| `notes` | Are intent, pattern, design, and answer status markers present when useful? | recommended |

## Approval Checklist

- [ ] The case came from a customer-neutral intent or manually reviewed risk.
- [ ] The draft was not auto-promoted to active.
- [ ] The customer-specific `expected_answer` was reviewed by a responsible human.
- [ ] The customer-specific `expected_evidence` was reviewed by a responsible human.
- [ ] Source documents remain in the vendor or customer-controlled environment.
- [ ] The case does not include customer raw logs, retrieved chunks, or full source text.
- [ ] The case has an owner for future change review.
- [ ] The case can be validated by `validate-pack`.
- [ ] The case is ready to be executed by `rqg eval` and `rqg gate` only after it is active.

## Recommended Notes Markers

| Marker | Purpose |
|---|---|
| `intent:<intent_id>` | Links an active case back to an abstract intent |
| `pattern:<failure_pattern>` | Links the case to a failure pattern |
| `design:<test_design_type>` | Records test design intent |
| `release:block` | Indicates a release-gate blocking intent |
| `release:needs_human_review` | Indicates escalation is required |
| `answer_status:vendor-approved` | Indicates the expected answer was approved for active case use |

## Do Not Approve If

- The expected answer is still a generated draft.
- The source evidence is missing or customer-specific review is incomplete.
- The case relies on customer raw data copied into the case text.
- The source document ownership or effective date is unclear.
- The case is intended to make a final contract, legal, or customer-specific
  exception decision without a responsible reviewer.

## Related Flow

See [Intent to Case Draft Flow](intent_to_case_draft_flow.md).
