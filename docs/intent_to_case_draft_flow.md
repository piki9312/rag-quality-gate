# Intent to Case Draft Flow

## Purpose

This document explains how the file-based Case Intent Library should be used to
create future review candidates without changing Proof Gate runtime contracts.

## Source of Truth

Active formal `cases.csv` is the only runtime source of truth.

The Case Intent Library is not executable by `rqg gate`. It does not replace
`cases.csv`, and it does not change GateDecision, `gate-report.json`, or
ReviewPacket.

## Flow

```text
Case Intent Library
  -> needs_review draft
  -> human review
  -> active cases.csv
  -> validate-pack
  -> eval
  -> gate
  -> Review Packet
```

## Step Details

| Step | Owner | Output | Notes |
|---|---|---|---|
| Case Intent Library | Proof Gate / vendor asset owner | abstract intent | Contains no customer raw data or customer-specific expected answers |
| needs_review draft | future draft workflow | review candidate | Must not be active by default |
| human review | vendor/customer reviewer | approved case row or pending/rejected candidate | Customer-specific expected answer and evidence are reviewed here |
| active `cases.csv` | vendor/customer-controlled pack | runtime case | Only active formal rows are executable |
| validate-pack | Engineer / QA | validation result | Checks formal pack compatibility |
| eval | Engineer / QA | evaluation result | Runs approved cases only |
| gate | Engineer / QA | GateDecision and reports | Uses active cases only |
| ReviewPacket | PM / delivery lead | release review artifact | Summarizes gate result and review context |

## Draft-Cases CLI

A `draft-cases` CLI may be added later. It is future work and is not part of
this task.

Until such a workflow exists, the seed library should be treated as design
material for humans to create or review candidate cases.

## Boundaries

The library must not contain:

- customer names
- customer documents
- raw answers
- retrieved chunks
- customer-specific `expected_answer`
- customer-specific `expected_evidence`

Draft candidates conceptually start as `needs_review`. They can only become
runtime evidence after human approval and entry into active formal `cases.csv`.

## Human Approval Requirements

Before an S1 intent becomes an active case, a reviewer should confirm:

- the source document reference
- the customer-specific expected answer
- the customer-specific expected evidence
- the risk category and severity
- the evaluation mode
- the owner for unresolved ambiguity
- the notes markers needed for traceability

## Compatibility Notes

This flow does not change:

- formal `cases.csv` schema
- `rqg eval`
- `rqg check`
- `rqg gate`
- GateDecision
- `gate-report.json`
- ReviewPacket
