# Case Intent Library

## Purpose

This directory contains a file-based seed library of abstract S1 release-gate
case intents for Proof Gate.

The Case Intent Library is not a runtime case source. It is planning material
for creating vendor-reviewed draft cases.

## Runtime Boundary

Active formal `cases.csv` remains the only runtime source of truth for:

- `rqg eval`
- `rqg check`
- `rqg gate`
- GateDecision
- `gate-report.json`
- ReviewPacket

Proof Gate must not execute this library directly. A Case Intent can only become
runtime evidence after it is turned into a draft, reviewed by a human, approved,
and entered into active formal `cases.csv`.

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

## What This Library May Contain

The library may contain reusable, customer-neutral review design material:

- intent IDs
- risk domains
- failure patterns
- business risk descriptions
- abstract question templates
- expected behavior types
- prohibited behavior descriptions
- evidence requirement types
- recommended evaluation modes
- human review field requirements
- block reason templates
- notes marker suggestions

## What This Library Must Not Contain

Do not store customer-specific material here:

- customer names
- customer documents
- raw questions
- raw answers
- retrieved chunks
- source document text
- customer-specific `expected_answer`
- customer-specific `expected_evidence`
- customer-specific contract terms
- customer-specific prices
- customer-specific operational exceptions

## S1 Seed

The initial S1 seed lives under `s1_seed/`.

It defines 12 initial intents across six risk domains:

- `refund_cancellation`
- `pricing_billing`
- `contract_terms`
- `eligibility_scope`
- `deadline_procedure`
- `support_policy`

These intents are intentionally conservative. Each intent is a prompt for human
case design and vendor/customer review, not an executable test case.

## Status Values

Current seed status values are descriptive only:

- `seed`: initial library seed, not yet validated by customer deployments
- `candidate`: proposed for future library expansion
- `deprecated`: retained only for historical reference

Status does not make an intent executable.

## Future Work

A future `draft-cases` workflow may read this library and create `needs_review`
draft candidates. That CLI is not part of this task and is not required for
current runtime behavior.
