# Partner Operating Model

## Purpose

This document defines the operating model for vendors using Proof Gate as a Partner Platform.

[Partner Platform Model](partner-platform-model.md) defines what Proof Gate gives, shows, and retains.

Partner Operating Model defines who uses which interface, when they use it, and what operational responsibility each role owns.

When a change event affects case coverage, the operating model should follow [Change-Aware Case Management](change-aware-case-management.md): Proof Gate may propose or warn, but vendors approve customer-specific runnable cases.

For the workflow-level DX model and case approval split, see [AI Quality Management DX Model](ai-quality-management-dx-model.md) and [Case Intent Library Design](case-intent-library-design.md).

This is a strategy and operations document. It does not change CLI, Dashboard, ReviewPacket, `gate-report.json`, safe/full implementation, schemas, Docker packaging, authentication, database, or multi-tenant behavior.

## Operating Principle

CLI / Runner is for execution.

Dashboard is for review and decision.

Customer-facing safe report is for external submission.

Safe aggregation is for Proof Gate-side improvement.

In Japanese:

- 実行はCLI / Runner。
- 判断はDashboard。
- 顧客提出はcustomer-facing safe report。
- Proof Gate側の改善はsafe集計。

This means not every vendor-side user is expected to operate a terminal.

Engineers and QA run validation, gates, retests, adapters, and artifact generation. PMs and delivery leads review the dashboard. Sales and CS use customer-facing safe reports for explanation and submission. Proof Gate receives only safe aggregation unless an explicit customer-controlled agreement says otherwise.

## Vendor-Side Roles

| Role | Primary Interface | Responsibility |
|---|---|---|
| Engineer / QA | CLI / Runner | `pack validate`, gate execution, RAG endpoint connection, retest, run artifact generation |
| PM / Delivery Lead | Dashboard | Judge No-Go reasons, S1/S2 blockers, improvement priority, customer submission readiness, production release readiness |
| Sales / CS | customer-facing safe report | Customer explanation, report submission, residual risk explanation |
| Vendor Admin / Tech Lead | local/private environment | Manage customer documents, `cases.csv`, `change-event.yml`, and full/private details |

PMs and delivery leads may also use the AI案件レビューキット templates under
`templates/customer-rqg-template/reviews/templates/` to record scope,
behavior boundaries, release risk, and customer/vendor confirmation items.
Sales / CS may use the same kit to understand which safe report and residual
risk notes are ready for customer explanation. These templates are review
materials, not terminal workflows.

## Proof Gate-Side Roles

| Role | Responsibility |
|---|---|
| Partner Success | Initial onboarding, monthly partner review, operational consultation |
| Quality Asset Owner | Improve Quality Packs, Failure Patterns, severity guidance, and report language |
| Product Owner | Improve Runner, Dashboard, Report, and safe/full policy |

In the earliest phase, one person may hold multiple roles. The roles should still be separated conceptually because they optimize different parts of the Partner Platform.

## Initial Operating Flow

1. Vendor Engineer / QA runs pack validation.
2. Vendor Engineer / QA runs the gate.
3. Vendor Engineer / QA passes `change-event.yml` when reviewing a change.
4. Run artifact, gate report, ReviewPacket, and customer-facing report are generated.
5. PM opens the Dashboard.
6. PM reviews Delivery Review, S1/S2 Blocking List, Production Readiness, and Customer Submission Readiness.
7. If the result is No-Go, engineers fix the issue and rerun the gate.
8. If the result is Go or Conditional, PM reviews the customer-facing safe report.
9. Sales / CS submits or explains the report to the customer.
10. Monthly safe aggregation is shared with Proof Gate when agreed, and Proof Gate uses it to improve Quality Packs, Failure Patterns, report language, and operating support.

## Interface Responsibility

### CLI / Runner

Primary users:

- Engineer / QA

Uses:

- pack validate
- gate execution
- `change-event.yml` loading
- RAG endpoint execution
- mock execution
- artifact generation
- report generation

CLI / Runner is the execution interface. It is not the main PM review surface.

### Dashboard

Primary users:

- PM / Delivery Lead
- QA Lead
- Tech Lead

Uses:

- delivery judgment
- production release judgment
- critical blocker review
- improvement action review
- customer submission readiness review

Dashboard is the internal vendor review surface. It should not be treated as the customer submission artifact.

### Customer-Facing Safe Report

Primary users:

- PM
- Sales / CS
- customer

Uses:

- customer submission
- explanation of quality review result
- residual risk explanation
- change review result sharing

The customer-facing safe report is the external artifact. It must preserve the safe/full boundary.

### Safe Aggregation

Primary users:

- Proof Gate-side team
- Vendor PM / Tech Lead

Uses:

- monthly partner review
- Quality Pack improvement
- Failure Pattern improvement
- report language improvement
- operating model improvement

Safe aggregation is not a full evidence upload. It should contain bounded summary data, not raw customer content.

## Source Sharing / Distribution Policy

As a default, do not give vendors Proof Gate source code.

In early sales or onboarding, show:

- demo Dashboard screens
- sample customer-facing reports
- sample `change-event.yml`
- sample Quality Pack structure
- sample runbooks
- safe/full policy guidance

During controlled validation, avoid sharing the whole repository. Prefer Proof Gate-side execution support, a minimal execution environment, or a narrow partner kit.

If source sharing is unavoidable, require:

- NDA
- defined usage scope
- limited access period
- no reuse outside the agreed pilot
- no redistribution
- no derivative internal clone
- explicit handling rules for customer data and full evidence

For semi-commercial delivery, target packaged execution forms such as:

- packaged runner
- Docker image
- signed runner

These are future distribution options. They are not assumed to be implemented today.

## Distribution Phases

### Phase 0: Demo / Sales

- Do not share source.
- Proof Gate-side team runs the demo locally.
- Show Dashboard screen, sample customer-facing report, and sample `change-event.yml`.
- Use fictional, sample, or redacted data only.

### Phase 1: Controlled Pilot

- Limit to one trusted partner or a tightly scoped pilot.
- Prefer Proof Gate-side execution support.
- Share only the minimum required execution environment.
- Avoid full repository sharing.
- Keep customer data in vendor or customer-controlled environments.

### Phase 2: Packaged Runner

- Provide CLI / Runner as a packaged runner or Docker image.
- Vendor executes without seeing source.
- Customer data remains in the vendor environment.
- Safe usage summary can be shared back when agreed.
- Packaged runner and Docker image are future candidates, not current implementation assumptions.

### Phase 3: Partner Runner / Protected Asset Loading

- Version standard Quality Packs and decision policies.
- Allow partners to use protected core assets without receiving the raw asset base.
- Keep the option open for remote asset service or signed asset bundles.
- Continue keeping full/private customer data outside Proof Gate-side storage.

### Phase 4: Hosted Partner Platform

- SaaS
- database
- authentication
- multi-tenant workspaces
- partner administration UI

This is a future phase. Do not build it now.

## Do / Do Not

### Do

- Separate interfaces by role.
- Let PMs make review decisions without terminal operation.
- Limit customer submission artifacts to safe reports.
- Keep full/private detail in vendor or customer-controlled environments.
- Use only safe aggregation for Proof Gate-side improvement.
- Keep source distribution narrow until packaged runner options are ready.

### Do Not

- Require every vendor-side user to operate a terminal.
- Treat Dashboard as the customer submission artifact.
- Put raw question, answer, or evidence in customer-facing reports.
- Distribute the full repository as the Partner Kit.
- Collect customer data into Proof Gate-side systems before SaaS and data governance are intentionally designed.
- Build authentication, database, or multi-tenant infrastructure in the initial phase.

## Compatibility Notes

This operating model must remain compatible with:

- CLI argument backward compatibility
- existing `gate-report.json` fields
- ReviewPacket structure
- safe/full evidence boundary
- local/private/customer-controlled full evidence handling
- Windows PowerShell local usage

Future runner or packaging work should be additive and should not require PMs, Sales, or CS to use the terminal for review and submission decisions.
