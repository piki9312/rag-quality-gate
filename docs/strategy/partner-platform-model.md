# Partner Platform Model

## Purpose

This document defines how Proof Gate can be provided to AI/RAG delivery vendors as a Partner Platform without handing over the full internal product asset base.

The operating principle is:

> Give partners enough to use Proof Gate.
> Do not give partners enough to clone Proof Gate's core review assets and decision logic.

This document complements [Partner Kit Asset Inventory](partner-kit-asset-inventory.md). It describes the responsibility boundary, not a new implementation.

For role-level operation details, see [Partner Operating Model](partner-operating-model.md). The Partner Platform is initially operated through CLI / Runner + Dashboard + customer-facing safe report. Execution, review decision, and customer submission should be separated by role, and the Partner Kit does not assume full source-code distribution.

## Partner Platform Position

Proof Gate is used by vendors, SIers, and AI delivery teams that run quality reviews for their own customers.

The partner-facing promise is:

- partners can run review workflows in their own or customer-controlled environment
- partners can produce internal dashboard evidence for delivery review
- partners can produce safe customer-facing reports
- partners can keep full customer evidence local
- Proof Gate retains the standard review logic, Quality Pack strategy, failure patterns, and report generation know-how

## Three Asset Classes

| Asset class | Partner access | Examples |
|---|---|---|
| Give | Partner can receive and run it. | runbooks, demo packs, sample `change-event.yml`, customer project template, safe/full policy guide, customer-facing sample copy |
| Show but do not fully give | Partner can see examples, screenshots, excerpts, or guided usage. | dashboard examples, ReviewPacket concept, reason taxonomy overview, severity examples, report examples |
| Retain | Proof Gate keeps the full asset or implementation detail. | standard Quality Pack library, full Failure Pattern library, decision logic details, report generation internals, accumulated cross-customer learning |

## Responsibility Boundary

The most important boundary is between customer-specific assets and Proof Gate standard assets.

| Area | Vendor / customer owns | Proof Gate owns |
|---|---|---|
| Customer cases | Customer-specific `cases.csv`, expected behavior, expected answers, category mapping. | Case schema, validation rules, standard templates, severity guidance. |
| Customer documents | Customer FAQ, terms, pricing table, HR policy, internal rules, document versions. | Document corpus review policy, stale document signals, source-of-truth guidance. |
| Customer changes | Actual document, prompt, retriever, model, or policy changes. | `change-event.yml` structure, review-stage interpretation, change impact review pattern. |
| Evaluation execution | Running against customer RAG endpoints and storing full evidence locally. | Gate engine, adapter boundary, report mode policy, safe/full exposure rules. |
| Standard review assets | Optional partner-visible excerpts only. | Standard Quality Packs, Failure Patterns, severity/decision heuristics, reporting logic. |
| Customer-facing output | Final approval to share with the customer. | Safe report template, submission readiness logic, customer-facing language patterns. |

## Data Boundary

Full/private data must remain in the partner, vendor, private runner, or customer-controlled environment.

Full/private data includes:

- raw question text
- raw AI answer text
- raw retrieved evidence
- source document path
- raw document name
- customer-specific metadata
- full JSONL logs
- full `gate-report.json` generated from real customer data
- full ReviewPacket generated from real customer data

Proof Gate-side shared outputs should be limited to safe summaries:

- hashed or bounded IDs
- severity counts
- safe reason codes
- category counts
- review stage
- release decision status
- customer submission readiness
- safe report reference
- timestamps and partner-controlled identifiers

## Dashboard And Report Boundary

The dashboard is for partner internal review.

It can help PMs, QA, and technical leads decide what to fix, what to approve, and what cannot be released yet. It should not be treated as the customer submission artifact.

The customer-facing report is the safe artifact.

It should avoid full evidence, raw answers, raw questions, source paths, owners, and customer-private metadata unless the customer explicitly controls and approves that disclosure.

## Partner Kit Minimum

A safe Partner Kit can include:

- product positioning one-pager
- runbook for local execution
- demo Quality Pack
- demo `change-event.yml`
- sample customer project template
- safe/full evidence policy
- customer-facing report sample
- submission checklist
- PowerShell-compatible commands

It should not include:

- accumulated customer-derived packs
- complete Failure Pattern database
- full test suite
- full report generation internals as reusable templates
- real customer data
- production full report bundles

## Operating Model

Recommended operating flow:

1. Partner receives Partner Kit and demo pack.
2. Partner runs demo locally using sample data.
3. Partner copies customer project template into its own or customer-controlled repo.
4. Partner adds customer-specific cases and documents.
5. Partner runs Proof Gate locally or in a private runner.
6. Partner uses dashboard for internal remediation.
7. Partner generates customer-facing safe report only when submission readiness allows.
8. Partner shares safe summary or agreed monthly review data back to Proof Gate if applicable.

## Protected Asset Boundary

Proof Gate should retain:

- standard Quality Pack strategy
- Failure Pattern library
- severity and decision heuristics
- ReviewPacket and readiness logic
- safe/full policy implementation
- report generation logic
- cross-customer improvement notes

Partners should retain:

- customer-specific cases
- customer-specific expected behavior
- customer documents
- customer endpoint configuration
- full run evidence
- customer approval records unless otherwise agreed

## Non-Goals For Now

Do not build a hosted partner portal yet.

Do not build multi-tenant partner workspaces yet.

Do not build automatic Partner Kit generation yet.

The current phase should keep the Partner Platform model document-led and CLI/report-led.
