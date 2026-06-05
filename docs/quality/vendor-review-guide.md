# Vendor Review Guide for Case Artifacts

## Purpose

This guide defines how vendors should review case artifacts before they become
formal `cases.csv` rows.

Review artifacts are not formal `cases.csv` assets. They are candidate case
artifacts for human review. Generated `expected_answer` values are unapproved
drafts until a vendor or customer-side reviewer confirms them.

Proof Gate supports coverage and draft generation. The vendor is responsible for
customer-specific correctness approval.

For the underlying Case Intent Library raw-data boundary, see
[Case Intent Library Data Boundary](../strategy/case-intent-library-data-boundary.md).
For the bounded `notes` marker contract, see
[Case Notes Marker Spec](case-notes-marker-spec.md).

## Artifact Types

| Artifact | Role | Approval state | Next step |
| --- | --- | --- | --- |
| Old `review.csv` | Lightweight review candidate output from document-based `gen_cases` | Candidate only | Human review, then existing `merge-cases` adoption flow |
| PatternDraft `pattern-draft-review.csv` | Pattern-based review candidate rows from Case Intents and source sections | Candidate only | Human review, then existing review/merge adoption flow |
| `review_cases.yaml` | Structured vendor review file generated from `needs_review` draft rows | Vendor-editable review record | `approve-cases` |
| `review_cases.md` | Human-readable preview of `review_cases.yaml` | Preview only | Do not treat as machine source of truth |
| Formal `cases.csv` | Gate execution input | Approved-for-run only when `status=active` | `rqg eval` / `rqg gate` / `rqg check` |

## Review Artifact Boundary

Review artifacts can include generated questions, expected answers, evidence
references, source hints, severity hints, and trace markers. These values are
not release evidence by themselves.

Do not treat a generated `expected_answer` as a customer-approved answer just
because it appears in `review.csv`, `pattern-draft-review.csv`, or
`review_cases.yaml`.

The formal boundary is:

```text
review artifact
  -> vendor/customer review
  -> approved active row in cases.csv
  -> Gate execution
```

Only `status=active` rows in formal `cases.csv` are Gate execution targets.

## Decision Semantics

`review_cases.yaml` uses explicit review decisions.

| Decision | Output status | Meaning | Gate execution target |
| --- | --- | --- | --- |
| `approve` | `active` | Vendor confirmed the case is correct for this customer | Yes |
| `pending` | `needs_review` | More review or customer clarification is needed | No |
| `reject` | `deprecated` | Do not use this generated candidate | No |

`approve-cases` applies only approved review entries to active rows. Pending and
rejected entries remain outside Gate execution.

## Answer Status Markers

Proof Gate uses bounded `notes` markers to avoid adding schema fields too early.

| Marker | Meaning |
| --- | --- |
| `answer_status:unapproved-draft` | The generated expected answer has not been vendor/customer approved |
| `answer_status:vendor-approved` | A vendor-side reviewer approved the answer during review |

Approved active cases must not retain `answer_status:unapproved-draft`.

Pending and rejected cases may retain `answer_status:unapproved-draft` because
they are not approved-for-run.

Markers should contain abstract IDs and review state only. Do not put customer
raw FAQ text, inquiry logs, contract wording, pricing details, or full
customer-specific expected answers in `notes`.

## How To Review Expected Answers

Before setting `decision: approve`, confirm that:

- `expected_answer` matches the customer's current business rule.
- The answer is not merely copied from stale or partial source text.
- Required exceptions, escalation conditions, and human-review triggers are
  included when they matter.
- The answer can be defended against the cited evidence.

If any of these are unclear, keep the case as `pending` or reject it.

## How To Review Evidence

Before approval, confirm that:

- `expected_evidence` points to the current customer document or approved source.
- `source_doc` is the intended document or policy source.
- The evidence still exists and has not been superseded.
- The case does not expose raw/private evidence outside the vendor/customer
  controlled environment.

## Severity Review

Formal runtime `cases.csv` supports `S1` and `S2` severity.

Some planning documents or Case Intent hints may use `S3` / `S4` as design or
coverage hints, but those are not formal runtime severities. Do not approve a
formal runtime case with `S3`, `S4`, empty, or unknown severity.

## Old `review.csv`

Old `review.csv` remains a review candidate artifact. It is useful for
document-based `gen_cases` review and the existing `merge-cases` adoption flow.

Important boundaries:

- It is not a formal `cases.csv`.
- Generated `expected_answer` values are unapproved drafts.
- The marker `answer_status:unapproved-draft` should remain in `notes` when a
  generated answer is shown for reviewer convenience.
- Human review is still required before the case becomes approved-for-run.

## PatternDraft Review Artifact

PatternDraft outputs `pattern-draft-review.csv`-style rows. These rows use the
formal field order so existing review/merge tooling can inspect them, but their
meaning is still "generated review candidate."

Important boundaries:

- Output rows must remain `status=needs_review`.
- `answer_status:unapproved-draft` must be retained.
- Active rows must not be emitted by PatternDraft.
- Vendor approval is required before any row becomes `active`.

## `review_cases.yaml`

`review_cases.yaml` is the structured review source for `approve-cases`.

Machine-owned fields:

- `case_id`
- `suggestion`
- initial `status=needs_review`

Vendor-owned review fields:

- `decision`
- `vendor_review.expected_answer`
- `vendor_review.expected_evidence`
- `vendor_review.expected_keywords`
- `vendor_review.severity`
- `vendor_review.eval_mode`
- `vendor_review.reviewed_by`
- `vendor_review.reviewed_at`
- `vendor_review.notes`

The vendor should edit `review_cases.yaml`, not `review_cases.md`, when deciding
whether a draft case can become active.

## Sample Workflow

```text
sample docs
  -> cases_draft.csv
  -> rqg export-case-review
  -> review_cases.yaml + review_cases.md
  -> vendor edits review_cases.yaml
  -> rqg approve-cases
  -> cases.csv
  -> rqg eval / rqg check / rqg gate
```

Recommended command sequence:

```bash
rqg export-case-review \
  --draft cases_draft.csv \
  --output-yaml review_cases.yaml \
  --output-md review_cases.md

rqg approve-cases \
  --draft cases_draft.csv \
  --review review_cases.yaml \
  --output cases.csv

rqg eval cases.csv --docs documents --mock
rqg check --log-dir logs
```

## Do Not

- Do not auto-promote generated cases to `active`.
- Do not treat generated `expected_answer` as a formal answer key.
- Do not make Gate execute `needs_review`, `draft`, or `deprecated` rows.
- Do not upload customer raw evidence unless the vendor/customer boundary allows it.
- Do not use `review_cases.md` as the machine-readable approval source.
