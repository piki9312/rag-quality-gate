# GTM 0 To 10

## Goal

The first go-to-market phase should prove that RAG Quality Gate can help delivery teams move customer RAG and FAQ agents from PoC to production operation. The target is not broad self-serve SaaS adoption yet. The target is 0 to 10 customer deployments with a repeatable CLI, Quality Pack, external adapter, and reporting workflow.

## Ideal Early Customers

- RAG delivery vendors with several similar customer projects.
- AI implementation consultancies selling paid PoCs.
- Teams delivering HR, labor, policy, or internal-rule FAQ agents.
- Teams with customer pressure to explain why an agent is safe enough to ship.

## Entry Point

Start with a narrow promise:

> We add a repeatable quality gate around your customer-facing RAG agent so S1 failures are caught before rollout and reports can be shared with stakeholders.

The first conversation should focus on delivery risk, manual validation cost, and customer accountability rather than evaluation-framework sophistication.

## Initial Offer

Use a service-assisted product motion:

- One customer pack.
- One or two high-risk document groups.
- 10 to 30 curated cases.
- S1/S2 severity split.
- `rqg gate` run before customer demo or production handoff.
- Report package: Markdown report, `gate-decision.json`, and `gate-report.json`.

## Sales Motions

### Motion A: PoC Hardening

Use when the customer has a working prototype but no repeatable quality process.

Deliverables:

- Initial Quality Pack.
- First gate report.
- List of S1 blockers and next actions.

### Motion B: Vendor Delivery Standard

Use when a RAG vendor wants a repeatable QA layer across projects.

Deliverables:

- Pack template.
- External RAG contract.
- CI or scheduled gate example.
- Monthly review workflow.

### Motion C: Production Trust Review

Use when a deployed RAG system has stakeholder concern after content or model changes.

Deliverables:

- Regression case set.
- Baseline/current comparison.
- Gate decision and review notes.

## Learning Loop

For each customer deployment, record:

- Which documents created the highest-risk cases.
- Which `failure_type` and `failure_category` appeared most.
- Which next actions were reusable.
- Which external RAG contract differences needed adapter handling.
- Which report fields customers actually used.
- Which manual steps repeated across customers.

Reusable patterns should move into docs, templates, tests, or code. One-off customer details should stay outside shared implementation.

## 0 To 10 Success Criteria

- At least 10 customer or customer-like packs have run through `rqg gate`.
- S1 blocking is understood and accepted by delivery teams.
- `gate-report.json` is useful to at least one downstream review or issue workflow.
- External RAG integration works without making local RAG the product identity.
- Most repeated onboarding issues are covered by `validate-pack` or documentation.

## After 10 Deployments

Consider UI, authentication, workspaces, and hosted operations only after repeated evidence shows that CLI/report workflows are the bottleneck rather than case design, adapter integration, or service delivery.
