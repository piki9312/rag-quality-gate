# Evaluator Adapter Contract

## Purpose

This document defines the strategy-level contract for accepting results from internal or external evaluators and converting them into Proof Gate review artifacts.

It is not an implementation spec yet. It is a product and architecture contract for future implementation.

## Position

Proof Gate should not compete with every evaluator.

Proof Gate should sit above evaluators and convert their outputs into release review decisions, ReviewPackets, production readiness signals, customer submission readiness, and safe reports.

```text
EvaluatorResult
  -> NormalizedFailure
  -> ReviewPacket
  -> Decision / Production Readiness / Customer Submission / Report
```

## Evaluator Types

Evaluator inputs may come from:

- internal `rqg gate`
- rule-based checks
- RAGAS
- LLM-as-judge
- retrieval evaluation
- answer correctness evaluation
- Zendesk or support QA
- human review
- future external evaluation APIs
- customer-specific scoring pipelines

The evaluator may be automated, human-assisted, or fully human.

## Contract Boundary

The Evaluator Adapter is different from the existing external RAG adapter.

| Adapter | Purpose |
|---|---|
| External RAG adapter | Normalizes a customer RAG endpoint response into a shape Proof Gate can evaluate. |
| Evaluator Adapter | Normalizes an evaluator's result into failures, severity, evidence status, review need, and decision impact. |

The external RAG adapter sits before or during evaluation.

The Evaluator Adapter sits after evaluation and before ReviewPacket generation.

## Minimal Input Shape

An evaluator result should be mappable to the following conceptual fields:

| Field | Meaning | Safe/full note |
|---|---|---|
| `evaluator_name` | Source evaluator or review method. | Safe if bounded. |
| `evaluator_version` | Version or model/config identifier. | Safe if not customer-secret. |
| `case_id` | Case or item reference. | Prefer hashed or bounded ID in safe mode. |
| `category` | Business or risk category. | Safe if bounded. |
| `severity` | S1/S2/S3 or equivalent. | Safe. |
| `score` | Optional numeric score. | Safe if not derived from private text. |
| `passed` | Whether the evaluator considered the item passing. | Safe. |
| `reason_code` | Fixed normalized reason code. | Safe. |
| `reason_text` | Free-form explanation. | Full/private unless sanitized and bounded. |
| `evidence_status` | Whether evidence supports, contradicts, or is missing. | Safe as status only. |
| `evidence_pointer` | Pointer to full evidence. | Safe only if opaque and non-identifying. |
| `requires_human_review` | Whether human review is required. | Safe. |
| `decision_impact` | How this affects release/submission. | Safe. |

## NormalizedFailure

The adapter should convert evaluator-specific output into `NormalizedFailure`-like records.

Required conceptual fields:

- stable item id
- severity
- category
- normalized reason code
- evidence status
- release impact
- required action candidate
- safe explanation
- full evidence pointer when available

The normalized record should not expose raw questions, raw answers, raw evidence, source paths, owners, or customer-private metadata in safe mode.

## Reason Normalization

Evaluator free-form output must not flow directly into CI-safe output, dashboard safe views, or customer-facing reports.

Evaluator output should be mapped to controlled reason codes such as:

- `evidence_mismatch`
- `stale_reference`
- `major_misguidance`
- `business_rule_violation`
- `missing_source_of_truth`
- `stale_doc_policy_missing`
- `change_event_missing`
- `affected_documents_missing`
- `retest_trigger_unclear`

The controlled reason code can be displayed as auxiliary metadata. The PM/customer-facing explanation should be localized and bounded.

## Safe/Full Handling

Safe evaluator output may include:

- evaluator name
- bounded evaluator version
- case hash or bounded ID
- severity
- category
- reason code
- evidence status
- decision impact
- required action category

Full/private output may include:

- raw question
- raw AI answer
- raw retrieved evidence
- judge rationale
- support transcript
- source path
- owner
- customer-specific document name
- full evaluator payload

Full/private output must remain local, private-runner, or customer-controlled.

## ReviewPacket Integration

The adapter should feed ReviewPacket generation, not bypass it.

Evaluator output should not directly become:

- customer-facing report
- production release decision
- formal submission recommendation
- dashboard final decision

Instead, Proof Gate should combine normalized evaluator results with:

- review stage
- change event
- Quality Pack scope
- severity policy
- production readiness policy
- customer shareability policy
- customer submission readiness policy
- human approval or risk acceptance if applicable

## Near-Term Implementation Guidance

Do not implement multiple evaluator integrations immediately.

Recommended sequence:

1. Define a local `NormalizedFailure` shape or derived mapping over existing failure records.
2. Add one import path for a simple JSON evaluator result fixture.
3. Confirm it can produce the same ReviewPacket outputs as internal gate failures.
4. Add tests that safe output does not leak raw evaluator payload.
5. Only then consider RAGAS, LLM-as-judge, or human review import adapters.

## Non-Goals For Now

- replacing RAGAS
- building a new LLM judge framework
- storing full evaluator payloads in Proof Gate SaaS
- exposing evaluator free-form rationales in customer reports
- building a generic evaluator marketplace
