# Change-Aware Case Management

## Purpose

This document defines how Proof Gate should use change events to understand which cases are relevant, which cases are missing, and which draft cases may need to be proposed.

This is a strategy and design document. It does not introduce schema changes, automatic case selection, case coverage warning implementation, draft case generation, or document impact analysis implementation.

The goal is to extend the existing Failure Pattern-driven S1/S2 case design without breaking it.

```text
Before:
Failure Pattern -> S1/S2 Case

After:
Change Event -> Affected Category -> Relevant Failure Pattern -> Required S1/S2 Case
```

The change event is not the direct source of truth for a runnable case. It is an input for selecting which categories and Failure Patterns need coverage.

For the reusable Case Intent and Question Variation asset model behind future draft proposals, see [Case Intent Library Design](case-intent-library-design.md). For how `gen_cases` should create draft cases without activating them, see [gen_cases Redesign](gen-cases-redesign.md). For the developer-facing implementation sequence, see [Pattern-Based gen_cases Implementation Plan](pattern-based-gen-cases-implementation-plan.md).

## Current State

Current repo behavior:

- `cases.csv` has a `status` field.
- Current status values include `draft`, `active`, `needs_review`, and `deprecated`.
- Gate execution primarily runs `active` cases.
- `change-event.yml` is used as context for ReviewPacket, readiness warnings, Dashboard display, and reports.
- Change-event-based case selection is not implemented.
- Case coverage warning for affected categories is not implemented.
- Draft case proposal is not implemented.

This current behavior should remain stable while the design is validated.

## Target Model

The target model is:

```text
change-event
  -> affected_business_categories
  -> relevant Quality Pack domains
  -> relevant Failure Patterns
  -> existing active cases coverage check
  -> coverage warning if missing
  -> draft case proposal if needed
  -> vendor review
  -> active approved-for-run cases
  -> gate execution
```

The first implementation step should not be automatic case selection. It should be advisory coverage warning.

## Case Lifecycle

Current statuses should keep their current schema shape. Their operating meaning should be clarified as follows.

| Current Status | Operational Meaning | Future Equivalent |
|---|---|---|
| `draft` | 未承認のケース候補 | `draft` |
| `needs_review` | ベンダー確認待ち | `vendor_review_required` |
| `active` | 正式実行対象 | `approved-for-run` |
| `deprecated` | 廃止・旧ケース | `retired` |

Operating rules:

- Only `active` cases are treated as approved-for-run.
- `needs_review` cases require vendor review and should not be formal gate execution targets.
- `draft` cases are proposals and should not be used for formal decisions.
- `deprecated` cases are retired and should not be used for current release decisions.

Do not add new `approved` or `retired` statuses until repeated partner usage proves they are needed.

## Case Types

Do not add a case type schema field yet.

Future case types may include:

- `baseline`
- `change-impact`
- `regression`
- `customer-critical`
- `previous-failure`
- `generated-draft`
- `vendor-approved`

For now, case type can be expressed with bounded notes markers when needed:

```text
notes: case_type:baseline
notes: case_type:change-impact
notes: pattern:stale_reference
```

These markers should remain advisory until they are validated through partner pilots.

## Failure Pattern Compatibility

S1/S2 cases should continue to be designed from Failure Patterns.

The current case creation principle remains:

```text
Failure Pattern -> S1/S2 Case
```

Change-aware case management extends this principle:

```text
Change Event
  -> Affected Category
  -> Relevant Failure Pattern
  -> Required S1/S2 Case
```

The change event helps choose which Failure Patterns need coverage. It does not replace Failure Pattern-driven case design.

Example:

```text
change-event affected category: refund
  -> relevant failure patterns:
     - refund_rule_reversal
     - stale_reference
     - exception_overgeneralization
     - human_review_skipped
  -> check whether required S1/S2 cases are active
```

Start with category coverage. Later, move to Failure Pattern coverage.

## Case Coverage Warning

The first future implementation should be coverage warning, not case selection.

Minimal advisory rule:

```text
If review_stage is post_delivery_change
and change-event has affected_business_categories,
then for each affected category:
  check whether at least one active case exists in that category.
```

Warning example:

```yaml
case_coverage_missing:
  cancellation category has no active approved-for-run case
```

Stronger warning example:

```yaml
high_priority_case_coverage_missing:
  refund category has no active S1/S2 case
```

Coverage warning should be advisory at first.

It should not automatically change Go/No-Go until validated in pilots.

Rationale:

- Changing executed cases can change `GateDecision`.
- Cases outside the changed category can still break.
- Running all active cases preserves current gate semantics.
- Advisory warnings allow partners to test whether coverage signals are useful before they affect release decisions.

Therefore, the initial policy is:

- Continue running all active cases.
- Add coverage warning for affected categories.
- Do not automatically narrow execution based on `change-event.yml`.
- Do not automatically change `GateDecision`.

## Review Stage Policy

### `pre_delivery`

Primary case intent:

- baseline cases
- customer-critical cases
- selected S1/S2 cases
- selected Quality Pack domains

Purpose:

- confirm delivery readiness before customer submission or production discussion
- catch known high-risk answer failures before handoff

### `post_delivery_change`

Primary case intent:

- check active cases for affected business categories
- prioritize previous failures in the future
- emit case coverage warning when affected categories lack active approved-for-run cases
- propose draft cases in a future phase

Purpose:

- confirm changed documents, prompts, retrievers, models, or policies did not break high-risk answers

### `monthly_review`

Primary case intent:

- baseline cases
- previous failures
- sampled S1/S2 cases
- customer-critical cases

Purpose:

- monitor residual quality risk and maintenance drift

Review-stage-based case selection is not implemented today. This section defines direction only.

## Quality Pack Relationship

Proof Gate owns:

- Quality Pack structure
- Failure Pattern strategy
- standard case intent
- severity guidance
- coverage warning policy
- report and readiness interpretation

Vendors own:

- customer-specific `cases.csv`
- expected answers
- expected behavior
- customer documents
- customer-specific approval of case correctness

Proof Gate can propose draft cases from Quality Pack and Failure Pattern knowledge. The vendor must review business correctness before cases become `active`.

Proof Gate proposes case drafts.
The vendor approves customer-specific cases.
Only active cases are treated as approved-for-run.

In Japanese:

- Proof Gateはケース候補を提案する。
- ベンダーは顧客固有ケースの業務正しさを確認して承認する。
- `active` のケースだけを正式な実行対象、つまり approved-for-run として扱う。

Do not distribute the full standard Quality Pack or full Failure Pattern database as the Partner Kit.

## Document Impact Analysis Relationship

Document Impact Analysis and Change-aware Case Management are different layers.

| Layer | Purpose |
|---|---|
| Document Impact Analysis | Detect what changed from document v1/v2 diffs or related upstream inputs. |
| Change-aware Case Management | Use `change-event.yml` or impact analysis output to decide which case coverage is needed and which cases are missing. |
| Gate Execution | Run approved cases and generate Decision / ReviewPacket / Report. |

Do not implement Document Impact Analysis now.

The initial design should rely on human-authored `change-event.yml`.

Future document impact analysis may generate a change-event draft. A vendor should review it before it becomes the official change event for release review.

## Safe/Full Boundary

Customer-specific `cases.csv` can be full/private.

As a default, do not send these to Proof Gate-side systems:

- raw question
- expected answer
- raw answer
- raw evidence
- source path
- owner
- customer-specific document metadata

Safe usage summary may include aggregated or bounded fields:

- category
- severity
- Failure Pattern code
- coverage status
- count of active cases per category
- count of active S1/S2 cases per category
- review stage
- warning code

If Proof Gate supports draft case proposal, storage and sharing must be handled carefully. Customer-specific case text should remain in vendor or customer-controlled environments unless a specific agreement permits otherwise.

## Implementation Roadmap

### P0: Docs Only

- Add this `change-aware-case-management.md` document.
- Define `active` as approved-for-run.
- Define `needs_review` as vendor review required.
- Define advisory coverage warning behavior.

### P1: Coverage Warning

- Compare `affected_business_categories` with active cases.
- Add warning to Production Readiness.
- Show warning in Dashboard / report.
- Do not change `GateDecision`.

### P2: Failure Pattern Coverage

- Check coverage by Failure Pattern, not only by category.
- Use notes markers first, or a future field only after validation.
- Keep compatibility with current `cases.csv`.

### P3: Draft Case Proposal

- Propose draft cases from Quality Pack and Failure Pattern knowledge.
- Manage proposed cases as `draft` or `needs_review`.
- Vendor reviews expected answer / expected behavior.
- Vendor activates approved cases.

### P4: Document Impact Analysis

- Generate change-event candidates from v1/v2 document diffs.
- Vendor reviews and approves the change event.
- Feed the approved change event into change-aware case management.

## Non-Goals For Now

- schema changes
- new `cases.csv` columns
- ReviewPacket changes
- CLI changes
- Dashboard changes
- `gate-report.json` changes
- automatic case selection
- coverage warning implementation
- draft case generator
- document impact analysis
- Quality Pack database
- Failure Pattern database
