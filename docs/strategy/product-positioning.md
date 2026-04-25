# Product Positioning

## Positioning

RAG Quality Gate is a quality-assurance layer for customer-facing RAG and FAQ agents. It helps delivery teams move a RAG implementation from paid PoC to production operation by making answer-quality checks repeatable, reportable, and gateable.

It is not a generic RAG evaluation CLI, a full RAG framework, or a broad LLMOps platform. The product value is in making quality degradation visible before release and making the result explainable to customers and operators.

## First Target Users

- RAG delivery vendors building customer-specific assistants.
- AI implementation consultancies moving PoCs into customer operations.
- Small to mid-sized teams delivering internal-document search or FAQ agents.
- Teams that need a practical quality layer but are not ready to build a custom evaluation platform.

## First Use Cases

- High-risk document FAQ.
- Internal policy and procedure RAG.
- HR, labor, compliance, and internal-rule FAQ agents.
- Customer-facing or employee-facing agents where incorrect answers reduce trust or create accountability risk.

## Core Value

- Continuously verify RAG answer quality.
- Detect quality degradation caused by document updates, prompt changes, retrieval changes, or model changes.
- Block S1 critical cases before production rollout.
- Produce `gate-report.json` and Markdown reports for customer-facing explanation and internal review.
- Reduce manual validation work for delivery vendors.
- Convert paid PoC work into monthly quality operations.

## What To Avoid For Now

- Full SaaS product.
- Multi-tenant database.
- Authenticated customer dashboard.
- Billing and entitlement systems.
- Heavy UI.
- Generic LLMOps platform scope.

## Product Boundary

The near-term product should stay centered on:

- CLI workflows.
- Quality Pack structure.
- Formal `cases.csv` governance.
- External RAG adapter contract.
- Machine-readable and human-readable reports.
- Repeatable review and gate operations.

Customer-specific work should be documented as strategy or service learning first. Only repeatable patterns should become shared implementation.
