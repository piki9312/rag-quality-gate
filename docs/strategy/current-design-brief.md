# Current Design Brief

## Purpose

This short brief is for contributors aligning on the current Proof Gate product design.

## Current Position

Proof Gate should be understood as an AI quality management DX platform.

It is not only an AI/RAG evaluator.

It supports case design, vendor approval, release review, customer-safe reporting, and continuous quality asset improvement.

## Case Asset Principle

Customer-specific `expected_answer` is not a Proof Gate core asset.

Proof Gate's core reusable assets are:

- Case Intent
- Failure Pattern
- Question Variation
- Expected Behavior Template
- Severity Hint
- Evidence Requirement
- Coverage Rule

Proof Gate is responsible for coverage support:
which risks, Failure Patterns, Case Intents, and Coverage Rules should be considered.

The vendor is responsible for customer-specific correctness:
whether the `expected_answer` / `expected_behavior` is correct for the customer business.

日本語では、Proof Gateはカバーすべきリスク観点・Failure Pattern・Case Intent・Coverage Ruleを支援する。ベンダーは顧客固有の `expected_answer` / `expected_behavior` が業務上正しいかを承認する。

## gen_cases Principle

`gen_cases` is not a formal case generator.

`gen_cases` is a draft generator.

Generated cases should be `needs_review` by default.

Vendor approval is required before generated cases become `active`.

Only `active` cases are Gate execution targets.

## Next Implementation Candidates

Recommended next implementation sequence:

1. Make `gen_cases` output `needs_review`.
2. Add `notes` markers such as `generated_by`, `intent`, and `pattern`.
3. Keep case coverage warning advisory.
4. Add a small Case Intent Library.

## Boundaries

Do not treat customer-specific expected answers, customer documents, raw questions, raw answers, or raw evidence as Proof Gate-side assets by default.

Keep full/private data in vendor or customer-controlled environments.
