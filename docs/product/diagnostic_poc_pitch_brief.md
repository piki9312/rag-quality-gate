# Diagnostic PoC Pitch Brief

This pitch brief reuses existing Proof Gate PoC offer material, customer-safe
deliverable guidance, and Review Packet guidance, but reframes them for first
call, discovery, and PoC proposal conversations.

このpitch briefは、既存のDiagnostic PoC資料とReview Packet説明資料を、初回
ヒアリングやPoC提案で使いやすい形に再構成したものです。新しいruntime仕様
ではなく、営業・提案前の共有資料です。

## One-line Pitch

Proof Gateは、RAG/FAQボットの納品前に、重大な誤案内、根拠不一致、本番反映
リスクを確認し、Review Packetとして整理する納品前レビューPoCです。

English version:

> Proof Gate is a pre-delivery review PoC for RAG and FAQ bots. It checks
> high-risk answer failures, evidence mismatch, and release readiness signals,
> then organizes the results into a Review Packet for human release decisions.

## Target Customers

Primary targets:

- AI implementation vendors.
- RAG delivery vendors.
- FAQ bot / customer-support AI development teams.
- Teams operating AI answers for pricing, cancellation, refund, eligibility,
  deadline, procedure, contract, or support-policy questions.
- PMs or delivery leads who need customer-facing review evidence before handoff.

This is not positioned as a generic LLM evaluation platform. It is positioned as
a review layer for AI delivery vendors that need to explain whether a customer
RAG/FAQ system is ready to move forward.

## Problems To Confirm

Use the first call to confirm whether the customer has these problems:

- Critical answer failures are hard to find before RAG/FAQ delivery.
- It is difficult to see whether answers match the source documents.
- Old pricing, deadline, cancellation, or policy information may still be used.
- Customer-facing review material takes too much manual effort to prepare.
- The team does not know which questions to retest after a document or prompt
  change.
- Review work depends on individual PM or QA experience.

Good discovery questions:

- What does the target AI answer?
- Are refund, pricing, cancellation, deadline, eligibility, or procedure topics
  in scope?
- How do you currently review AI answers before delivery?
- Do you already prepare customer-facing review evidence?
- Have you seen issues with stale documents, evidence mismatch, or overclaiming?
- After policy or document changes, how do you decide which questions to retest?
- Which result would be most useful from a PoC: risk discovery, review effort
  reduction, or customer-facing evidence?

## What Proof Gate Does

Proof Gate helps the vendor team:

- Select high-risk review perspectives for S1/S2 cases.
- Convert review intent into customer-specific active `cases.csv` through human
  review.
- Evaluate RAG/FAQ answers against expected behavior and evidence.
- Check evidence, grounding, relevance, and stale reference risks.
- Run `rqg validate-pack`, `rqg eval`, and `rqg gate`.
- Organize S1/S2 risks, representative failures, evidence status, and next
  actions.
- Produce Review Packet, `gate-report.md`, `gate-report.json`, and
  `customer-summary.md` style artifacts.

When explaining Case Intent Library to customers, avoid making it sound like a
customer-facing database. Use this framing:

> Proof Gate uses high-risk review perspectives such as refund, pricing,
> deadline, and procedure risks to help design customer-specific review cases.
> The formal runtime source of truth remains the human-reviewed active
> `cases.csv`.

## Diagnostic PoC Flow

Recommended short flow:

```text
1. Confirm scope
2. Receive customer-approved or synthetic documents
3. Select S1/S2 review perspectives
4. Create and human-review cases.csv
5. Run validate-pack, eval, and gate
6. Create Review Packet
7. Hold review meeting
8. Propose remediation retest, change review, or monthly review
```

The flow should make clear that Proof Gate does not automatically approve
production release. It organizes evidence so humans can make an informed release
decision.

## Deliverables

Typical Diagnostic PoC deliverables:

- Review Packet.
- `gate-report.md`.
- `gate-report.json`.
- `customer-summary.md` or equivalent customer-safe summary.
- S1/S2 major risk list.
- Representative failure examples.
- Evidence / grounding check results.
- Recommended remediation memo.
- Retest or monthly review proposal.

The Review Packet should be treated as the main customer discussion artifact.
Machine-readable JSON remains useful for automation, but it should not be the
first artifact shown in a business review meeting.

## Initial Duration And Pricing Hypothesis

This is an initial commercial hypothesis, not a fixed price list.

| Package | Typical duration | Typical scope |
| --- | --- | --- |
| Light | 1 week | About 5 high-risk review cases |
| Standard | 1-2 weeks | About 10-15 high-risk review cases |
| Extended | 2-4 weeks | Around 20 or more cases, plus broader review discussion |

Pricing and scope should be adjusted based on:

- Number of documents.
- Whether a real RAG endpoint is connected.
- Number of S1/S2 review cases.
- Whether customer-facing reporting is required.
- Whether post-remediation retest is included.

Avoid presenting these as guaranteed fixed prices until repeated customer
delivery evidence exists.

## Expected Value

The pitch should center on these values:

- Earlier discovery of critical answer failures.
- Visibility into answer and evidence mismatch.
- Customer-facing review evidence before handoff.
- Reduced manual review preparation effort.
- Clearer retest scope after remediation.
- Connection to monthly review or post-change review operations.
- A more accountable AI delivery process before production handoff.

## Out Of Scope / Caution

State these boundaries clearly:

- Proof Gate is not a quality guarantee.
- Proof Gate is not a legal judgment.
- Proof Gate is not an AI safety certification.
- Proof Gate does not automatically decide production approval.
- Proof Gate does not cover every future AI answer.
- Proof Gate does not store customer raw data in the Case Intent Library.
- Case Intent Library is not the runtime source of truth.
- Active formal `cases.csv` is the runtime source of truth.
- Customer-specific expected answers and evidence must be reviewed by humans.

Recommended wording:

> Proof Gate is not an automated final approval system. It organizes review
> evidence, high-risk failures, and release readiness signals so humans can make
> informed release decisions.

Japanese version:

> Proof Gateは最終判断を自動化するものではありません。重大リスク、根拠確認、
> レビュー証跡を整理し、人間が本番反映判断を行うための材料を提供します。

## First-call Question List

Use these questions in the first discovery call:

- What AI or RAG/FAQ bot is being reviewed?
- Which documents or policies are in scope?
- Which domains create the biggest risk: refund, pricing, cancellation,
  deadline, eligibility, procedure, support policy, or contract terms?
- How are answers reviewed before customer handoff today?
- Do you already produce customer-facing review evidence?
- Have there been past issues with stale information, evidence mismatch, or
  incorrect policy answers?
- How often do documents, prompts, or retrieval settings change?
- Is the PoC goal risk discovery, review evidence, remediation prioritization,
  or ongoing monitoring?

## Relationship To Existing Materials

This pitch brief connects existing materials into a first-call explanation:

- `docs/sales/proof-gate-poc-offer.md`: PoC offer concept and follow-up options.
- `docs/sales/proof-gate-poc-security-and-deliverables.md`: data handling and
  deliverable boundaries.
- `docs/product/sample_review_packet_guide.md`: how to explain the Review
  Packet.
- `packs/release_review_demo`: customer-like release review demo pack.
- `docs/case_intent_draft_examples.md`: examples of Case Intent to
  `needs_review` draft candidate translation.

This document does not replace those materials. It condenses them for sales,
proposal, and first-call discussion.
