# Sample Review Packet Guide

This guide explains how to present a Review Packet during a Diagnostic PoC or
pre-release review discussion with an AI vendor, PM, reviewer, or customer-side
owner.

This document is non-runtime. It does not define active cases, replace formal
`cases.csv`, change `gate-report.json`, or modify the ReviewPacket contract. It
is a customer-facing explanation guide for reading the review artifact.

この文書はruntime入力ではありません。正式な`cases.csv`、Gate判定、
ReviewPacket、`gate-report.json`の代替ではなく、診断PoCや納品前レビューで
Review Packetをどう説明するかを整理するためのガイドです。

## Purpose

The Review Packet is not an AI safety guarantee, a legal approval, or a blanket
quality certification. It is a structured review artifact that helps teams decide
whether AI answers should move toward production, remain blocked, or receive
targeted remediation.

The Review Packet should organize:

- S1/S2 risk findings.
- Evidence mismatch, missing evidence, or stale evidence findings.
- Answer failures and representative examples.
- Recommended remediation actions.
- Human review notes and release decision context.

For Diagnostic PoC usage, the Review Packet is the main deliverable. Its value is
not that it says "everything is safe"; its value is that it makes release risk,
review evidence, and next actions visible to the vendor and customer-side owner.

## Recommended Structure

A Diagnostic PoC Review Packet should be organized in this order:

1. Executive Summary
2. Evaluation Scope and Target
3. Review Perspectives Executed
4. Gate Result / Policy Status
5. S1 Major Risk List
6. S2 Caution Risk List
7. Representative Failure Examples
8. Evidence / Grounding Check Results
9. Change Event / Baseline Comparison Differences, if present
10. Recommended Remediation Actions
11. Human Review / Decision Notes
12. Next Review / Monthly Review Proposal

This structure keeps the discussion practical: first show the release signal,
then the reasons, then the remediation path.

## Executive Summary Wording

Avoid wording that suggests Proof Gate guarantees total AI safety or legal
approval.

Do not write:

- "Quality guaranteed."
- "Safe."
- "Production-ready."
- "Legally no problem."
- "AI made the final decision."
- "All risks checked."

Prefer bounded review language:

- "Within this review scope, S1 major risks were detected."
- "This result is equivalent to BLOCK in Release Gate."
- "Before production, confirm the answer, evidence, and policy handling."
- "These findings should be treated as human review evidence."
- "Rerun the same high-risk cases after remediation."

Example:

> Within this review scope, S1 major risks were detected in refund and deadline
> handling. This is equivalent to BLOCK in Release Gate. Before production,
> confirm the answer behavior, supporting evidence, and policy interpretation,
> then rerun the same S1 cases after remediation.

## Gate Result / Policy Status

Gate status should be explained as a release review signal, not as an absolute
truth about the AI system.

- Gate PASS does not mean the AI system is completely safe.
- Gate FAIL / Policy BLOCK means critical risks were detected within the
  configured review scope.
- BLOCK is not an automatic final business decision. It is a signal that human
  review and remediation are required before release.
- In a Diagnostic PoC, BLOCK can be a successful outcome when it reveals S1 risks
  that were previously invisible.
- A No-Go demo is expected to detect S1 risks and show why the release should be
  blocked until remediation.

Recommended phrasing:

> The current result is BLOCK within the reviewed scope. This does not replace
> human release approval, but it indicates that production release should not
> proceed until the listed S1 issues are reviewed and remediated.

## S1 / S2 Risk Lists

The S1 and S2 lists should help reviewers quickly understand what blocks release
and what requires caution.

Recommended columns:

| Column | Purpose |
| --- | --- |
| `case_id` | Stable reference for follow-up and rerun. |
| `risk_domain` | Business area, such as refund, pricing, deadline, or support policy. |
| `severity` | S1 for release-blocking risk, S2 for major caution risk. |
| `failure_type` / `failure_pattern` | The type of answer or evidence failure. |
| `question` | The reviewed question or scenario. |
| Observed issue | What went wrong in the AI answer or evidence grounding. |
| Expected behavior | What the answer should do after human-approved policy review. |
| Evidence status | Whether evidence was aligned, missing, mismatched, or stale. |
| Business risk | Why this matters to release or customer trust. |
| Recommended action | What the vendor should fix or verify next. |

S1 should be explained as a release blocker candidate. S2 should be explained as
a caution risk that may not block release alone, but should be reviewed before a
customer-facing rollout.

## Representative Failure Examples

Representative failures make the packet easier to discuss in a customer meeting.
They should be concise and redact sensitive material when necessary.

Suggested structure:

- Question
- AI answer
- Expected answer
- Supporting evidence
- Actual issue
- Why it is critical
- Recommended remediation

Customer-facing versions may need redaction. Do not expose raw customer logs,
private source paths, or sensitive document excerpts unless the customer and
vendor explicitly control that artifact.

## Evidence / Grounding Check Results

Evidence findings should show whether the AI answer is supported by the expected
documents and whether the cited evidence is current.

The packet should make these states clear:

- Evidence aligned: the answer is supported by the relevant source.
- Evidence missing: the answer lacks sufficient supporting evidence.
- Evidence mismatch: the answer conflicts with the expected evidence.
- Stale evidence: the answer relies on outdated policy, pricing, deadline, or
  procedural information.
- Overclaim beyond evidence: the answer states more than the source supports.

This section should avoid vague statements like "RAG quality is low." Instead,
connect the issue to the evidence state and the business risk.

## Recommended Remediation Actions

Remediation should be concrete enough for a vendor team to act on.

Avoid:

- "Fix RAG."
- "Improve prompt."
- "Check documents."
- "Make it better."

Prefer:

- Align the FAQ refund policy answer to the latest contract terms.
- Remove stale pricing table references from the retrieval corpus.
- Add deadline handling to the cancellation procedure answer.
- Add human escalation conditions for refund exceptions.
- Rerun the same S1 case after remediation.

Each action should identify the affected risk domain, the likely owner, and the
expected rerun condition.

## Human Review / Decision Notes

The Review Packet should leave space for human decision notes. These notes should
record whether the reviewer approves release, blocks release, accepts residual
risk, or requests remediation.

Suggested note prompts:

- Is this S1/S2 finding accepted as valid?
- What remediation is required before release?
- Is any residual risk accepted by the customer or vendor owner?
- Which cases must be rerun?
- Who owns the next action?

## Post-PoC Next Actions

Recommended next steps after a Diagnostic PoC:

1. Fix S1 findings and rerun the same cases.
2. Run a change review after policy, document, prompt, or retrieval updates.
3. Add customer-specific active cases after human review.
4. Expand coverage using Case Intent Library candidates.
5. Establish a monthly quality review cadence.
6. Continue baseline comparison so regressions become visible.
7. Deliver Review Packets periodically as quality operations evidence.

## Review Language Checklist

Use these phrases:

- "Within this review scope"
- "As high-risk candidates"
- "Equivalent to BLOCK in Release Gate"
- "As human review evidence"
- "Recommended to confirm before production"
- "Rerun after remediation"

Avoid these phrases:

- "Quality guaranteed"
- "Safe"
- "Production-ready"
- "Legally no problem"
- "AI made the final decision"
- "All risks checked"

## Boundary Reminder

The Review Packet is a review artifact. It does not replace:

- Formal active `cases.csv`.
- Human release approval.
- Customer-owned policy interpretation.
- Legal review.
- Vendor remediation work.

The runtime flow remains:

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
