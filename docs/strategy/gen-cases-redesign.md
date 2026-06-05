# gen_cases Redesign

## Purpose

This document redefines `gen_cases` as a customer-specific draft case generator, not as a formal case generator.

This is a design document. It does not change CLI behavior, `gen_cases` implementation, `cases.csv` schema, ReviewPacket, Dashboard, or reports.

For the developer-facing implementation sequence for pattern-based `gen_cases` and the Case Draft Engine, see [Pattern-Based gen_cases Implementation Plan](pattern-based-gen-cases-implementation-plan.md).

## Current Role

Today, `gen_cases` is close to a mechanism that creates test case candidates from document sections.

That is useful, but it can be misleading if generated cases are treated as fully approved release evidence.

Document-derived case text and expected answers may still be wrong, incomplete, or misaligned with the customer's real business policy.

## New Role

Before:

```text
gen_cases = creates test cases from document sections
```

After:

```text
gen_cases = customer-specific draft case generator
```

Future:

```text
gen_cases = applies Case Intent / Failure Pattern / Question Variation
            to customer documents and change-events
            to generate needs_review cases
```

`gen_cases` should help vendors create reviewable case drafts. It should not bypass vendor approval.

## Output Status

gen_cases output must not become active by default.

Generated cases should default to one of:

- `needs_review`
- `draft`

Only vendor-approved cases should become `active`.

Only active cases are formal Gate execution targets.

This preserves the principle:

```text
Proof Gate proposes.
Vendor approves.
Gate runs active approved-for-run cases.
```

## Metadata Markers

Do not add schema fields yet.

Use bounded `notes` markers first:

```text
intent:refund_mid_contract_cancellation
pattern:refund_rule_reversal
case_type:generated-draft
generated_by:gen_cases
source:document_section
```

These markers should support traceability without breaking existing `cases.csv` compatibility.

## Generation Modes

Future modes:

### Document-Based Generation

Generate basic review cases from document sections.

Expected tendency:

- S2 / S3 leaning
- broad document coverage
- useful for initial draft portfolios

### Pattern-Based Generation

Generate risk-oriented cases from Failure Patterns and Case Intents.

Expected tendency:

- S1 / S2 leaning
- accident-inducing or edge-condition cases
- useful for release review and high-risk domains

### Change-Aware Generation

Generate draft cases based on `change-event.yml` affected categories.

Expected tendency:

- focused on changed business categories
- supports Change-aware Case Management
- still requires vendor approval before activation

## Safety And Responsibility

`expected_answer_draft` from `gen_cases` is unapproved.

Proof Gate does not automatically guarantee generated case correctness.

Generated cases become `active` only after vendor approval.

Customer raw data should not be stored on the Proof Gate side by default.

Full/private detail remains in vendor or customer-controlled environments.

Existing document-based `gen_cases` review output follows the same rule. Its
`review.csv` and review markdown are review candidate artifacts, not formal
`cases.csv` assets. When a generated `expected_answer` is shown for reviewer
convenience, the review artifact should keep the marker
`answer_status:unapproved-draft` in `notes` so reviewers do not mistake it for
a customer-approved answer.

For the operational vendor review boundary across old `review.csv`, PatternDraft
review artifacts, and `review_cases.yaml`, see
[Vendor Review Guide for Case Artifacts](../quality/vendor-review-guide.md).
The old `review.csv` path is still a review candidate artifact: it can be used
by existing review and merge workflows, but it is not itself an approved
`cases.csv` and must not be treated as release evidence until vendor review is
complete.

For the data boundary behind this design, see
[Case Intent Library Data Boundary](case-intent-library-data-boundary.md). The
library should hold abstract intents, failure patterns, claim templates, and
test design types. Customer-specific `expected_answer`, `required_claims`,
`forbidden_claims`, raw evidence, and source document body stay in
vendor/customer-controlled artifacts.

## Implementation Roadmap

Planned follow-up preparation before pattern-based `gen_cases`:

- a minimal `CaseDraftEngine` skeleton should create `needs_review` `DraftCaseCandidate` objects from Case Intents
- the skeleton should be template/mock-based and should not use an LLM
- it is a preparation step for future pattern-based `gen_cases`
- it should not be connected to the existing `gen_cases` CLI at first
- `CaseDraftPlanner` should combine affected business category candidate selection with the skeleton engine
- planner output should remain `needs_review` and should not be an approved-for-run case
- `SourceSectionMatcher` should connect Case Intents to document-section-like inputs through deterministic `evidence_requirement` matching
- source matching should remain a pre-generation support layer, not full retrieval and not a `gen_cases` CLI integration
- a row adapter should convert `CaseDraftPlanner` output to merge-compatible review candidate rows
- adapter rows should remain `needs_review` and should mark generated answers as `answer_status:unapproved-draft`
- `PatternDraftPipeline` should combine these internal pieces into affected categories + registry + sections -> `needs_review` review candidates
- a future pattern-based `gen_cases` CLI can call this pipeline, but the current CLI should remain unchanged
- an internal CSV writer should render pipeline output as a `review.csv`-style artifact before any CLI connection
- CSV writer output should remain vendor-review-only until the existing review/merge flow adopts it
- a preview artifact writer should produce a vendor-review CSV and row-count metadata
- this is the likely first boundary a future pattern-based `gen_cases` CLI should call

Alignment with the existing review flow:

```text
Case Intent Library / PatternDraftPipeline
  -> pattern-draft-review.csv candidate rows
  -> existing human review
  -> existing merge-cases adoption into cases.csv
  -> later vendor-approved active cases
```

Pattern-based generation should not create a new approval flow. It should produce candidate `review.csv` artifacts that the existing review and merge process can inspect.

### P0: Docs Only

- Redefine `gen_cases` as draft generation.
- Define the default `needs_review` direction.
- Keep existing implementation untouched.

### P1: needs_review Output

- Make `gen_cases` output `needs_review` by default.
- Add `generated_by`, `intent`, and `pattern` notes markers where available.
- Keep `active` promotion manual or vendor-approved.

### P2: Small Case Intent Library Connection

- Add a small internal Case Intent Library.
- Map selected intents to generated draft cases.
- Keep customer-specific answers vendor-owned.

### P3: Pattern-Based Generation

- Use Failure Patterns and Case Intents to generate S1/S2-oriented draft cases.
- Require vendor review before activation.

### P4: Change-Aware Generation

- Use `change-event.yml` affected categories to propose draft cases.
- Integrate with coverage warning trends.
- Keep formalization vendor-approved.

## Non-Goals For Now

- CLI changes
- `gen_cases` implementation changes
- `cases.csv` schema changes
- automatic activation of generated cases
- storing customer expected answers as Proof Gate assets
- storing customer raw documents on the Proof Gate side
