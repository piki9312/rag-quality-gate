# Diagnostic PoC Execution Guide

## Purpose

This guide defines the internal execution flow for the
`RAG/FAQ Bot Pre-Release Diagnostic PoC`.

It is intended for delivery teams running a short diagnostic PoC for AI vendors
or RAG implementation partners. It does not change runtime contracts, CLI
behavior, schema, GateDecision, ReviewPacket, or report JSON.

## Execution Flow

```text
Step 1: Scope confirmation
Step 2: Customer material intake
Step 3: Data/IP boundary confirmation
Step 4: S1/S2 review perspective selection
Step 5: Select S1 intents from Case Intent Library
Step 6: Create S2 candidates from document snapshot
Step 7: Create needs_review case drafts
Step 8: Human review
Step 9: Promote approved rows to active cases.csv
Step 10: validate-pack
Step 11: eval
Step 12: gate
Step 13: customer-facing Review Packet
Step 14: reporting meeting
Step 15: propose continuous review or monthly monitor
```

## Step Details

| Step | What to do | Input | Output | Notes |
|---|---|---|---|---|
| 1. Scope confirmation | Confirm target bot, release timing, and risky business domains. | Customer/vendor discussion. | PoC scope memo. | Keep the scope narrow enough for a short PoC. |
| 2. Customer material intake | Receive approved FAQ, terms, pricing, policy, procedure, or sample answer material. | Customer-approved documents. | Local/customer-controlled working pack. | Do not place raw customer data in shared common libraries. |
| 3. Data/IP boundary confirmation | Decide where docs, logs, keys, reports, and raw artifacts live. | Customer security constraints. | Data handling note. | Prefer local/private/customer-controlled storage for full data. |
| 4. S1/S2 perspective selection | Select high-risk review areas. | Scope memo and customer risks. | S1/S2 review perspective list. | Focus on refund, cancellation, pricing, contract, eligibility, deadline, support policy. |
| 5. Select S1 intents | Use Case Intent Library as an abstract design aid. | `case_intent_library/` seed. | S1 intent shortlist. | Library is non-runtime and does not define active cases. |
| 6. Create S2 candidates | Create lower-risk candidates from documents or existing examples. | Document snapshot. | needs_review S2 drafts. | Do not treat generated answers as approved. |
| 7. Create needs_review drafts | Convert review perspectives into draft rows. | Intent shortlist and documents. | needs_review review artifact. | Drafts are vendor-owned/customer-controlled artifacts. |
| 8. Human review | Confirm question, expected_answer, expected_evidence, severity, eval_mode, and block_reason. | review artifact. | approved / pending / rejected decisions. | Human approval is required before active use. |
| 9. Promote active cases | Copy only approved rows to formal active `cases.csv`. | approved review decisions. | active formal `cases.csv`. | Active `cases.csv` is the runtime source of truth. |
| 10. validate-pack | Validate pack structure and governance. | pack directory. | validation result. | Use strict S1 governance where appropriate. |
| 11. eval | Run evaluation against mock, local, or external RAG. | active cases and documents/RAG endpoint. | eval JSONL/provenance. | Execution mode must be disclosed. |
| 12. gate | Apply gate thresholds and policy. | eval output and gate config. | gate decision/report bundle. | `BLOCK` and `NEEDS_HUMAN_REVIEW` are decision support signals. |
| 13. Review Packet | Create customer-safe review output. | gate bundle. | Review Packet / customer summary. | Use safe/redacted modes for external sharing. |
| 14. Reporting meeting | Explain results, risk areas, and next actions. | Review Packet and risk list. | customer/vendor action memo. | Avoid saying quality is guaranteed. |
| 15. Follow-up proposal | Propose fix support, change review, or monthly monitor. | PoC outcome. | next offer. | Connect to continuous review only when useful. |

## Runtime Flow

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

Case Intent Library is not runtime input. `rqg gate` must not read it directly.

## Recommended Commands

Adjust paths to the customer or demo pack.

```powershell
.\.venv\Scripts\python -m rqg.cli validate-pack --pack-dir packs\release_review_demo --strict-s1-governance
.\.venv\Scripts\python -m rqg.cli eval --pack packs\release_review_demo --mock --log-dir demo_runs\diagnostic_poc_eval --reset-log-dir
.\.venv\Scripts\python -m rqg.cli gate --pack packs\release_review_demo --mock --change-event packs\release_review_demo\change-event.yml --log-dir demo_runs\diagnostic_poc_gate --reset-log-dir
```

For real customer work, replace mock/local settings with the agreed private
runner or external RAG adapter setup.

## Non-Goals

- Do not implement a new `draft-cases` CLI as part of this PoC package.
- Do not auto-promote generated cases to active.
- Do not change formal `cases.csv` schema.
- Do not change GateDecision, ReviewPacket, or `gate-report.json`.
- Do not store customer raw data in common assets or shared libraries.
