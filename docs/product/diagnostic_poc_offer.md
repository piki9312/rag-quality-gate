# RAG/FAQ Bot Pre-Release Diagnostic PoC

## Product Name

- English: `RAG/FAQ Bot Pre-Release Diagnostic PoC`
- Japanese: `RAG/FAQ繝懊ャ繝育ｴ榊刀蜑阪Ξ繝薙Η繝ｼ Diagnostic PoC`

## Positioning

This PoC is a diagnostic service package for AI vendors and RAG delivery teams
that need to review customer-facing RAG/FAQ bots before delivery, production
release, post-change rollout, or monthly quality operations.

Proof Gate is not an automated final approval system.
It organizes review evidence, high-risk failures, and release readiness signals
so humans can make informed release decisions.

譌･譛ｬ隱槭〒縺ｯ縲￣roof Gate縺ｯ譛邨ょ愛譁ｭ繧定・蜍募喧縺吶ｋ繧ゅ・縺ｧ縺ｯ縺ゅｊ縺ｾ縺帙ｓ縲・驥榊､ｧ繝ｪ繧ｹ繧ｯ縲∵ｹ諡遒ｺ隱阪√Ξ繝薙Η繝ｼ險ｼ霍｡繧呈紛逅・＠縲∽ｺｺ髢薙′譛ｬ逡ｪ蜿肴丐蛻､譁ｭ繧定｡後≧縺溘ａ縺ｮ
譚先侭繧呈署萓帙＠縺ｾ縺吶・
## Target Customers

- AI implementation vendors and RAG delivery companies.
- Teams delivering RAG/FAQ bots to customers.
- Customer-facing AI systems answering about FAQ, terms, pricing, cancellation,
  refund, support policy, or procedures.
- Delivery leads who need evidence before handoff, release approval, or change
  rollout.

## Problems Solved

- Critical mistakes are often found too late, just before or after delivery.
- It is hard to see whether answers and supporting evidence are aligned.
- Customer-facing review evidence takes too much manual work.
- After document, prompt, retriever, or model changes, teams do not know which
  risks to retest.
- PMs and customer owners need a clear release decision, not only raw evaluation
  scores.

## What The PoC Includes

- Scope confirmation for the target RAG/FAQ bot and business risks.
- S1/S2 high-risk case design for refund, cancellation, pricing, contract terms,
  eligibility, deadline, procedure, and support policy.
- Optional Case Intent Library based S1 draft selection.
- Human review before any S1 case becomes active.
- Evidence and grounding review.
- RAG answer evaluation.
- Release Gate execution.
- Review Packet / gate-report / customer-summary generation.
- Major risk summary and recommended remediation notes.

## Deliverables

- Review Packet.
- `gate-report.md`.
- `gate-report.json`.
- `customer-summary.md`.
- S1/S2 major risk list.
- Recommended remediation memo.
- Optional post-PoC monitor / monthly review proposal.

## Duration

| Plan | Typical duration | Intended use |
|---|---:|---|
| Light | 1 week | Narrow pre-release diagnostic for a limited FAQ or policy scope. |
| Standard | 1-2 weeks | Typical vendor/customer PoC with S1/S2 case review and Gate output. |
| Extended | 2-4 weeks | Larger scope, existing RAG adapter, change review, or monthly review transition. |

## Indicative Pricing

| Plan | Indicative price | Notes |
|---|---:|---|
| Light | JPY 50,000 | Small scope, limited documents and cases. |
| Standard | JPY 100,000-150,000 | Most initial vendor PoCs. |
| Extended | Around JPY 200,000+ | Larger scope, additional review, or external RAG adapter work. |

Pricing should be adjusted by document count, existing RAG connection work,
case count, report depth, and customer review meeting scope.

## Value

- Finds critical answer risks before customer delivery or production rollout.
- Reduces manual review effort by organizing cases, evidence, and reports.
- Gives PMs and customer owners a concrete release readiness view.
- Creates a bridge to continuous post-delivery review, change review, and monthly
  quality monitoring.

## Important Disclaimers

- This PoC does not guarantee AI answer quality.
- This PoC does not replace legal, compliance, or domain-owner judgment.
- This PoC does not automatically approve production release.
- The output is review evidence and decision support, not a warranty.
- Customer raw data and full/private evidence should remain in a local, private,
  or customer-controlled environment.
