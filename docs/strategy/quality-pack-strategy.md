# Quality Pack Strategy

## Purpose

This document defines the asset and responsibility model for Quality Packs, Failure Patterns, and customer-specific cases.

The goal is to keep Proof Gate useful to partners without giving away the full standard evaluation asset base or mixing customer-specific data into Proof Gate-owned assets.

## Core Principle

Customer-specific cases belong to the vendor or customer.

Proof Gate owns the standard review framework:

- Quality Pack structure
- validation rules
- severity guidance
- standard risk categories
- Failure Pattern strategy
- decision and report interpretation

This keeps customer data local while allowing Proof Gate to improve standard review quality over time.

## Asset Classes

| Asset | Owner | Shareability | Notes |
|---|---|---|---|
| Customer `cases.csv` | Vendor / customer | Not shared back by default. | Contains customer-specific behavior, expected answers, and risk assumptions. |
| Customer expected behavior | Vendor / customer | Not shared back by default. | Should be maintained by the delivery team with customer approval. |
| Customer FAQ / policy / pricing docs | Customer or vendor environment | Not shared back by default. | Source of truth remains outside Proof Gate. |
| Demo Quality Pack | Proof Gate | Shareable. | Uses fictional or sample data. |
| Standard Quality Pack pattern | Proof Gate | Partially visible. | Show examples, retain full library and evolution logic. |
| Failure Pattern library | Proof Gate | Excerpts only. | Full library is a core product asset. |
| Severity and decision heuristics | Proof Gate | Summary visible. | Full implementation and accumulated rules remain internal. |
| Report generation logic | Proof Gate | Output visible. | Full templates and readiness logic remain product assets. |

## Quality Pack Roles

Quality Packs should serve four roles:

1. Define the review scope.
2. Encode high-risk questions and expected behavior.
3. Map cases to severity, category, and failure pattern.
4. Feed ReviewPacket, dashboard, and customer-facing report generation.

They should not be framed as a complete guarantee of AI safety.

A PASS means the configured cases passed within the configured scope. It does not mean every future AI answer is correct.

## Standard Pack vs Customer Pack

Standard packs:

- provide reusable review patterns
- define common high-risk domains
- encode known failure modes
- help partners start faster
- should be versioned and governed by Proof Gate

Customer packs:

- contain customer-specific behavior
- reflect customer documents and business rules
- must be maintained by the vendor or customer
- should not be committed back to the public Proof Gate repo
- should run in customer-controlled or partner-controlled environments

## Failure Pattern Strategy

Failure Patterns are core Proof Gate assets.

They should capture recurring ways AI/RAG systems fail in delivery contexts:

- stale reference
- evidence mismatch
- business rule violation
- major misguidance
- missing source of truth
- stale document policy gap
- change event missing
- affected documents missing
- retest trigger unclear

Failure Patterns should be used to:

- guide case authoring
- normalize failures across evaluators
- explain release impact
- generate required actions
- support customer-facing safe explanations
- improve future standard packs

Do not expose the full Failure Pattern database as a partner deliverable in the current phase.

## Severity Strategy

Severity should connect evaluation results to delivery risk.

| Severity | Meaning | Release impact |
|---|---|---|
| S1 | Critical customer, legal, financial, safety, or trust risk. | Usually blocks release or formal submission until fixed or explicitly accepted. |
| S2 | Major business or operational risk. | Usually requires fix, mitigation, or conditional approval. |
| S3 | Lower risk quality issue. | May be tracked as improvement if S1/S2 are clear. |

Severity must be interpreted with review stage:

- `pre_delivery`: blocks or conditions customer delivery.
- `post_delivery_change`: blocks or conditions release of the changed behavior.
- `monthly_review`: informs residual risk, maintenance action, and partner/customer review.

## Quality Pack Metadata

Quality Pack metadata should remain additive and backward compatible.

Useful metadata fields include:

- `review_stage`
- pack name and version
- owner role
- customer-safe description
- target AI system type
- document corpus expectations
- source-of-truth expectations
- stale document policy expectations

Avoid adding mandatory metadata until repeated partner/customer runs prove the field is necessary.

## Governance

Proof Gate should maintain:

- standard pack version history
- failure pattern change notes
- severity guidance
- report interpretation guidance
- safe/full boundary rules

Partners should maintain:

- customer cases
- customer expected behavior
- customer document versions
- customer change events
- customer approval notes

## Near-Term Implementation Guidance

Do not build a full pack registry or database yet.

Near-term work should focus on:

- documenting standard vs customer asset boundaries
- improving pack validation warnings
- keeping demo packs clean and fictional
- adding pack metadata only when it supports review workflows
- ensuring ReviewPacket and dashboard can explain Quality Pack scope

## Non-Goals For Now

- public Failure Pattern database
- automatic standard pack marketplace
- SaaS pack registry
- customer data ingestion service
- broad industry taxonomy before repeated customer evidence
