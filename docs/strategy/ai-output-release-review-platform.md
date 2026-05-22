# AI Output Release Review Platform

## Purpose

This document defines Proof Gate as an AI Output Release Review Layer, not as a standalone RAG evaluator.

Proof Gate is for AI/RAG delivery organizations that need to decide whether AI answers or AI outputs are safe enough to move from PoC to delivery, from delivery to production, from change to release, or from monthly maintenance review to continued operation.

The operating model is role-separated: CLI / Runner handles execution, Dashboard supports PM release review decisions, and customer-facing safe reports are the external submission artifact. See [Partner Operating Model](partner-operating-model.md) for the vendor-side workflow.

## Core Positioning

Proof Gate is not just an evaluator.

Proof Gate is not the evaluator itself.

Proof Gate is the release review layer that turns evaluator outputs, evidence, change context, and severity into delivery decisions, customer-facing reports, and operational review artifacts.

In Japanese:

> Proof Gateは、AI/RAG開発会社・SIerが、PoC後・納品前・本番反映前・変更後・月次保守のタイミングで、AI回答やAI出力を本番に出してよいか判断するための品質レビュー基盤である。

RAG / FAQ AI is the first use case. It is not the final product boundary.

The long-term product boundary is AI output release review:

- RAG / FAQ answers
- generated customer-facing answers
- AI workflow outputs
- AI agent outputs
- AI-assisted operational decisions

Proof Gate should remain useful even when the underlying evaluator changes from internal rule checks to RAGAS, LLM-as-judge, human review, external QA APIs, or future model-provider evaluation tools.

## Target Users

Primary users are not end SMB buyers using a self-serve evaluation SaaS.

Primary users are delivery-side organizations:

- AI/RAG development companies
- SIers
- DX support companies
- AI implementation consultancies
- PM / QA / technical leads responsible for PoC-to-production delivery
- future AI delivery teams inside large SIers or consulting firms

These teams need a repeatable way to answer:

- Can this AI output be delivered?
- Can this changed AI behavior be released?
- Can this run be used as customer-facing evidence?
- What must be fixed before approval?
- What evidence can be shared safely?
- What full/private evidence must remain in the customer-controlled environment?

## Insertion Points

Proof Gate should support the following review moments.

| Review moment | Business meaning | Current implementation mapping |
|---|---|---|
| PoC Quality Check | Confirm the PoC is credible before moving to paid delivery or production discussion. | Usually maps to `pre_delivery` for now. |
| Pre-Delivery Review | Confirm answer quality before customer delivery. | `pre_delivery` |
| Release Gate | Confirm the AI output can be released to production. | Usually maps to `pre_delivery` or `post_delivery_change` depending on whether there is a change event. |
| Change Impact Review | Confirm changed documents, prompts, models, or retrieval settings did not break high-risk answers. | `post_delivery_change` |
| Monthly Quality Review | Confirm residual quality and operational risk during maintenance. | `monthly_review` |

Do not expand `review_stage` too early. `poc_quality_check` and `release_gate` can first be handled as business labels or report copy over the existing stage model until implementation evidence shows that new machine-readable stages are needed.

## Product Flow

Proof Gate should be explained as a transformation layer:

```text
Evaluator output / Gate run / Human review
  + Change context
  + Evidence status
  + Severity and failure pattern
  + Safe/full exposure policy
    -> ReviewPacket
    -> Delivery decision
    -> Production readiness
    -> Customer submission readiness
    -> Customer-facing safe report
    -> ReleaseDecision / operational review artifact
```

The evaluator detects signals. Proof Gate turns those signals into release review artifacts.

## What Proof Gate Owns

Proof Gate should own the decision workflow and review artifacts:

- ReviewPacket model and generation logic
- release review semantics
- severity and decision impact interpretation
- customer submission readiness
- safe/full evidence boundary
- customer-facing report generation
- change-to-decision trace structure
- standard Quality Pack strategy and failure pattern governance
- partner-facing operating model

Proof Gate should not claim to own all evaluation intelligence.

External or replaceable components may include:

- RAGAS
- LLM-as-judge
- internal rule checks
- customer-provided test cases
- human QA review
- external model-provider evaluation APIs
- vendor-specific scoring pipelines

## Strategic Differentiation

Proof Gate should avoid competing head-on with broad AI governance platforms.

The narrow wedge is delivery and release review:

- what changed
- what was tested
- what failed
- why it matters for release
- what must be fixed
- whether the customer-facing report is safe to share
- whether formal customer submission is recommended
- whether production release should be approved, blocked, or conditioned

This keeps Proof Gate closer to the PM / QA / delivery workflow than to generic model governance.

## Current Repo Fit

Current implementation already supports part of this direction:

- `ReviewPacket`
- dashboard rendering
- customer-facing markdown report
- `review_stage`
- `change-event.yml`
- Delivery Review
- Production Readiness
- Customer Shareability
- Customer Submission Readiness
- safe/full artifact boundary

The next design gap is to formalize:

- Evaluator Adapter Contract
- Change-to-Decision Trace
- Partner Platform asset boundary
- Quality Pack and Failure Pattern responsibility split

## Non-Goals For Now

Do not build these as part of this positioning shift:

- SaaS tenant workspaces
- authentication
- billing
- multi-tenant database
- generic AI governance dashboard
- customer data upload SaaS
- full AI agent / tool-use review framework
- public test-pack database
- public failure-pattern database

The near-term product should remain a CLI / Quality Pack / ReviewPacket / safe report workflow that can be operated in vendor or customer-controlled environments.
