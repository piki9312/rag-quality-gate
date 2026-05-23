# Change-to-Decision Trace

## Purpose

This document defines the target trace from a change event to a release or submission decision.

The goal is to explain not just that an AI answer failed, but why the failure matters for delivery or release.

For the case management layer between change events and gate execution, see [Change-Aware Case Management](change-aware-case-management.md).

Future trace rows may reference Case Intent and generated draft provenance. See [Case Intent Library Design](case-intent-library-design.md) and [gen_cases Redesign](gen-cases-redesign.md).

Proof Gate should help a PM answer:

- What changed?
- What assets or categories were affected?
- What was tested?
- What failed?
- What evidence status caused concern?
- Why does this affect release?
- What action is required?
- Can the customer-facing report be shared?
- Is formal customer submission recommended?

## Target Trace

```text
Change Event
  -> Affected Assets / Documents / Categories
  -> Test Cases / Evaluation Items
  -> Failure / Signal
  -> Evidence Status
  -> Decision Impact
  -> Required Action
  -> Customer Shareability
  -> Customer Submission Readiness
  -> ReleaseDecision / Review Outcome
```

This trace is a review and explanation structure. It does not require exposing full evidence in safe views.

## Current Implementation Mapping

Current repo concepts already cover parts of the trace.

| Trace step | Current implementation status |
|---|---|
| Change Event | `change-event.yml`, `ChangeEvent`, change summary. |
| Affected assets/categories | Partially represented by change metadata and category/failure aggregation. |
| Test cases / evaluation items | `cases.csv`, Quality Pack, gate run records. |
| Failure / signal | Gate failures, reason taxonomy, severity, failure type. |
| Evidence status | Partially represented by reason codes and report details. |
| Decision impact | GateDecision, Delivery Review, Production Readiness, Customer Submission Readiness. |
| Required action | `required_actions`, `next_actions`, dashboard action table. |
| Customer shareability | `customer_shareability`. |
| Customer submission readiness | `customer_submission_readiness`. |
| ReleaseDecision | Domain concept exists, but operational export/approval workflow is still weak. |

The gap is not absence of data. The gap is that the trace is not yet a first-class view or contract.

## Trace View Principles

The trace should be:

- review-stage aware
- safe/full aware
- readable by PMs and QA leads
- derived from existing report/ReviewPacket data where possible
- additive and backward compatible
- usable in dashboard and customer-facing safe summaries with different detail levels

The trace should not require a breaking change to `gate-report.json` or `ReviewPacket` in the first iteration.

## Stage-Specific Meaning

### `pre_delivery`

The trace explains why an AI answer is or is not ready for delivery.

Main question:

> Can this AI answer behavior be delivered to the customer?

If No-Go, the trace should push toward internal remediation and retest before customer submission.

### `post_delivery_change`

The trace explains how a change affected answer quality.

Main question:

> Can this changed AI behavior be released?

The trace should emphasize changed documents, changed policies, affected categories, stale references, and retest triggers.

### `monthly_review`

The trace explains residual risk and operational trend.

Main question:

> What quality risks remain in monthly maintenance, and what changed since the previous review?

The trace may include multiple changes or no specific change event.

## Safe Trace vs Full Trace

Safe trace may include:

- review stage
- change type
- bounded affected category
- severity
- reason code
- evidence status label
- decision impact label
- required action summary
- customer submission readiness

Full trace may include:

- raw question
- raw answer
- raw evidence
- source path
- owner
- raw document name
- full evaluator rationale
- customer-specific metadata

Safe trace should never require full evidence expansion.

## Minimal Trace Record

A future derived trace record can be shaped like this conceptually:

| Field | Meaning |
|---|---|
| `trace_id` | Stable safe identifier. |
| `review_stage` | `pre_delivery`, `post_delivery_change`, `monthly_review`, or `unknown`. |
| `change_ref` | Safe change reference if present. |
| `affected_category` | Bounded category such as refund, cancellation, pricing, document_corpus. |
| `case_ref` | Safe case reference or hash. |
| `severity` | S1/S2/S3. |
| `reason_code` | Controlled reason code. |
| `evidence_status` | Supported, missing, mismatch, stale, unknown. |
| `decision_impact` | Blocks release, requires review, conditions release, informational. |
| `required_action` | Bounded action summary. |
| `owner_role` | PM, QA, engineer, customer confirmation, legal, or unknown. |
| `next_state` | Retest, customer confirmation, document update, approval, risk acceptance. |

This should be generated from existing data before introducing schema changes.

## Dashboard Use

A dashboard trace card should eventually show:

- one-line change summary
- affected categories
- top S1/S2 trace rows
- why each row blocks or conditions release
- required action and owner role
- link or anchor to full/private detail only when full mode allows it

This card should sit below the initial overview and action cards, not replace them.

## Customer Report Use

Customer-facing reports should not show the full trace.

They can show a safe summary:

- review scope
- affected categories
- top safe risks
- unresolved blocker count
- required customer-visible action
- limitations and assumptions

No raw question, raw answer, raw evidence, source path, or owner should appear in customer-facing safe output.

## Near-Term Implementation Guidance

Recommended first implementation:

1. Add a derived trace builder over current ReviewPacket/report data.
2. Keep it optional and additive.
3. Add dashboard-only safe trace rows for S1/S2 failures.
4. Add tests for safe/full leakage.
5. Add customer report summary only after dashboard trace is stable.

Do not add a mandatory trace schema to `gate-report.json` until repeated reports prove the fields are stable.

## Non-Goals For Now

- full audit database
- cross-customer trace warehouse
- hosted evidence store
- automatic root-cause inference
- source document diff engine
- broad observability platform
