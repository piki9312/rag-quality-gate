# Case Intent Library Design

## Purpose

This document defines Proof Gate's reusable case design asset model.

Proof Gate's core asset should not be a customer-specific answer-key database. Its core assets should be reusable case intent, failure pattern, question variation, expected behavior template, severity hint, evidence requirement, and coverage rule design.

For how these assets should be loaded and applied by a future Case Draft Engine, see [Pattern-Based gen_cases Implementation Plan](pattern-based-gen-cases-implementation-plan.md).

For the data boundary that keeps customer raw data and customer-specific answer
keys out of the library, see
[Case Intent Library Data Boundary](case-intent-library-data-boundary.md).

Implementation status note: this document describes the planned design and
follow-up implementation sequence. A docs-only PR should not be read as proving
that the referenced source modules or asset files already exist.

Phase 1 planned implementation note:

- Case Intent assets will be loaded from YAML.
- Planned source location: `src/rqg/case_assets/`.
- Planned sample location: `assets/case_intents/`. The sample should be a minimal schema validation sample, not a full operational library.
- Case Intent YAML must not include customer-specific `expected_answer`.

Phase 2 planned implementation note:

- YAML-loaded Case Intents should be indexed by `CaseIntentRegistry`.
- Registry lookup should support `intent_id`, `risk_category`, `failure_pattern`, `severity_hint`, and `coverage_rule.required_when.affected_business_categories`.
- Registry candidate selection is the prerequisite for pattern-based `gen_cases` and future coverage warnings.
- Initial registry matching uses exact string matching; normalization or alias mapping can be added later.

## Core Idea

Proof Gate does not store customer-specific answer keys as its core asset.

Proof Gate stores reusable Case Intents, Failure Patterns, Question Variations, Expected Behavior Templates, Severity Hints, Evidence Requirements, and Coverage Rules.

In Japanese:

Proof Gateは顧客固有の正解付きテストケースを中核資産にしない。

Proof Gateは、顧客をまたいで再利用できるCase Intent / Failure Pattern / Question Variation / Expected Behavior Templateを中核資産にする。

Coverage Rule defines which Case Intent or active case is required for a given change-event, affected category, Failure Pattern, or severity.

This allows Proof Gate to support coverage while keeping customer-specific correctness approval with the vendor and customer.

## Standard Case Asset

A Standard Case Asset may contain:

- `domain`
- `risk_category`
- `failure_pattern`
- `case_intent_id`
- `case_intent`
- `question_pattern`
- `question_variation`
- `expected_behavior_template`
- `severity_hint`
- `evidence_requirement`
- `coverage_rule`

Example:

```yaml
case_intent_id: refund_mid_contract_cancellation
domain: customer_support
risk_category: refund
failure_pattern: refund_rule_reversal
severity_hint: S1
case_intent: 契約途中解約時の返金可否を確認する
question_pattern: 契約途中で解約した場合、返金されますか？
expected_behavior_template: >
  最新の返金・契約条件に基づき、返金可否、例外条件、人間確認要否を案内する。
evidence_requirement:
  - refund_policy
  - contract_terms
coverage_rule:
  required_when:
    affected_business_categories:
      - refund
      - contract_terms
    change_types:
      - document_update
      - policy_update
  minimum_active_cases:
    any: 1
    s1_or_s2: 1
```

This is not yet a committed schema. It is the design direction for standard case assets.

The Phase 1 implementation keeps this small and conservative: YAML schema validation, stable directory loading, duplicate `intent_id` rejection, and explicit rejection of customer-specific `expected_answer`.

## Coverage Rule

A Coverage Rule defines when a Case Intent should be considered required or relevant for review coverage.

Conceptually, Coverage Rule is a core Proof Gate asset.

Initial implementation direction:

- keep `coverage_rule` as an attribute inside the Case Intent Library
- use it to support advisory coverage warnings
- do not automatically change GateDecision based on coverage rules
- do not automatically promote generated cases to `active`

Future direction:

- extract Coverage Rules into a separate registry if repeated partner runs prove the need
- support coverage checks by affected category, Failure Pattern, severity, and review stage

Example interpretation:

- if `affected_business_categories` contains `refund`, the Case Intent becomes a coverage candidate
- `minimum_active_cases.any` can support warnings when no active approved-for-run case exists
- `minimum_active_cases.s1_or_s2` can support high-priority warnings when no S1/S2 active case exists

## What Proof Gate Stores / Does Not Store

| Asset | Stored by Proof Gate? | Reason |
|---|---|---|
| Case Intent | Yes | Reusable across customers. |
| Failure Pattern | Yes | Core quality asset. |
| Question Variation | Yes | Improves coverage. |
| Expected Behavior Template | Yes | Reusable behavior shape. |
| Coverage Rule | Yes | Defines when coverage is required or missing. |
| Customer `expected_answer` | No | Depends on customer business rules. |
| Customer documents | No by default | Full/private data. |
| Raw question / answer / evidence | No by default | Protected by safe/full boundary. |
| Approved customer `cases.csv` | Vendor-owned | Customer-specific inspection asset. |

## Relationship To gen_cases

`gen_cases` should apply the Case Intent Library to customer documents and change context to produce Customer Draft Cases.

```text
Standard Case Asset
  + Customer docs / document sections
  + change-event
    -> gen_cases
    -> Customer Draft Case
       status = needs_review
```

The generated case is not formal release evidence until the vendor reviews and approves customer-specific correctness.

## Relationship To Vendor Approval

Cases generated by `gen_cases` are not formal cases.

Generated cases are `draft` / `needs_review`.

The vendor reviews `expected_answer` / `expected_behavior`.

After vendor approval, the case can become `active`.

Only active cases are Gate execution targets.

## Coverage vs Correctness

Proof Gate is responsible for coverage support.

The vendor is responsible for customer-specific correctness approval.

In Japanese:

Proof Gateは、どのリスク観点を確認すべきか、どのFailure Patternをカバーすべきかを支援する。

ベンダーは、顧客固有の`expected_answer`が正しいかを確認する。

This division is important for Partner Platform operation. Proof Gate can improve reusable coverage assets without owning customer-private answer keys.

Operationally, this means Case Intent Library entries should carry abstract
intent, design, failure pattern, evidence type, and coverage information only.
Customer-specific `expected_answer`, `required_claims`, `forbidden_claims`, and
raw evidence belong in vendor/customer-controlled review artifacts and approved
customer `cases.csv` files.

## Growth Strategy

Do not start by trying to build tens of thousands of cases.

Initial target:

```text
5 categories
x 5 Failure Patterns
x 3 Case Intents
x 4 Question Variations
= 300 patterns
```

Grow the library from:

- safe usage summary
- coverage warning trends
- vendor feedback
- controlled pilot learnings
- recurring No-Go reasons
- deprecated or ineffective case analysis

## Non-Goals For Now

- building a public case database
- storing customer-specific answer keys
- storing customer documents
- committing real customer approved cases into this repo
- adding a new case schema before field evidence proves it is needed
