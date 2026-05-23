# AI Quality Management DX Model

## Purpose

This document defines Proof Gate as a DX platform for AI quality management workflows, not only as an AI/RAG evaluation tool.

For the developer-facing plan to turn Case Intent assets into customer-specific draft cases, see [Pattern-Based gen_cases Implementation Plan](pattern-based-gen-cases-implementation-plan.md).

## Core Definition

Proof Gate is not only an AI/RAG evaluation tool.

Proof Gate is a DX platform for AI quality management workflows: case design, vendor approval, release review, customer-safe reporting, and continuous quality asset improvement.

In Japanese:

Proof Gateは単なるAI/RAG評価ツールではない。

Proof Gateは、AI導入後に発生する品質管理業務、つまりケース設計、業務正しさの承認、リリース判断、顧客提出レポート、継続的な品質資産改善をDX化する基盤である。

The product value is not just running tests. The value is turning repeated AI delivery quality work into a managed workflow with clear roles, safe artifacts, review packets, and reusable quality assets.

## DX Target Workflows

Proof Gate should digitize and standardize the following workflows:

- test perspective design
- customer-specific draft case creation
- approval of `expected_answer` / `expected_behavior`
- AI answer evaluation
- Go / No-Go decision support
- customer-facing safe report generation
- post-delivery change review
- monthly quality review
- Quality Pack / Failure Pattern improvement

These workflows should remain useful for RAG / FAQ AI first, while leaving room for broader AI output release review later.

## Human Role Placement

The goal is not to remove humans.

The goal is to decide where human judgment belongs.

Traditional workflow:

- Humans repeatedly design S1/S2 cases from Failure Patterns.
- Humans visually inspect AI answers.
- Humans manually create customer-facing reports.

Proof Gate workflow:

- Proof Gate creates drafts from Case Intent, Failure Pattern, and Question Variation assets.
- Vendors approve customer-specific business correctness.
- Gate execution evaluates answers, emits warnings, and produces decisions.
- PMs use Dashboard to judge Go / No-Go and remediation priority.
- Sales / CS submits customer-facing safe reports.
- Proof Gate improves standard assets from safe summaries and partner feedback.

This keeps human accountability in the right places: business correctness, release judgment, and customer communication.

## Before / After

| Workflow | Before | After |
|---|---|---|
| Test perspective design | Humans redesign perspectives each time. | Standardized with Case Intent / Failure Pattern. |
| Case creation | Manual case writing. | Draft generation with `gen_cases`. |
| Correctness check | Personal or ad hoc review. | Vendor approval. |
| AI answer evaluation | Visual check or one-off scripts. | Gate execution. |
| Release decision | PM experience and intuition. | Dashboard-supported review. |
| Customer explanation | Manual documents. | Customer-facing safe report. |
| Continuous improvement | Individual know-how. | Quality Pack improvement from safe summary. |

## Relationship To Existing Concepts

| Concept | Relationship |
|---|---|
| AI Output Release Review Layer | The DX model is the operating workflow around the release review layer. |
| Partner Platform | Partners operate the workflow in vendor or customer-controlled environments. |
| ReviewPacket | ReviewPacket is the central review artifact generated from gate results and context. |
| Dashboard | Dashboard is the PM decision surface for release review and remediation priority. |
| Customer-facing safe report | The external artifact for customer explanation and submission. |
| safe/full boundary | The boundary that keeps customer-private detail out of shared artifacts. |
| Change-aware Case Management | The workflow that checks whether changed categories have enough approved cases. |
| Case Intent Library | The reusable standard asset base for draft case generation and coverage support. |

## Non-Goals For Now

Do not build or claim these in the current phase:

- removing human approval completely
- Proof Gate guaranteeing customer-specific `expected_answer`
- collecting customer raw data on the Proof Gate side
- SaaS tenant workspaces
- database-backed platform operation
- authentication
- multi-tenant administration
- broad generic AI governance coverage
- full Document Impact Analysis implementation

The near-term model is still CLI / Runner + Dashboard + customer-facing safe report, operated with local, private, or customer-controlled full evidence.
