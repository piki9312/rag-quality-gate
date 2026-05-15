# Proof Gate PoC Security And Deliverables

## Proposal Summary

Proof Gate PoC checks more than aggregate AI/RAG answer scores. It tests
high-risk questions such as refunds, cancellation, pricing, terms, escalation,
and policy rules, then turns the result into a Gate Review that explains whether
the change can move forward.

For customer-facing delivery, GitHub Actions keeps only safe summaries. Full
questions, expected answers, AI answers, retrieved evidence, chunk text, and
customer documents stay in local, private runner, or customer-controlled
environments.

## Data Handling

| Area | PoC rule |
|---|---|
| GitHub-hosted Actions | Use sample, mock, dummy, or aggregate metadata only. |
| CI artifacts | Keep safe summaries only. Do not upload raw JSONL, full reports, vector indexes, or raw RAG payloads. |
| Full reports | Use only in local, private runner, or customer-controlled environments. |
| Customer documents | Use customer-approved or sanitized documents. Do not commit private material unless the customer repo and agreement allow it. |
| API keys | Store in environment variables, GitHub Secrets, or customer secret management. Never write them into the repo. |
| External RAG | Prefer staging, test, or read-only endpoints during PoC. |

## Report Modes

| Mode | Use | Customer-facing meaning |
|---|---|---|
| `ci` | GitHub Actions and automated checks. | Safe summary only. |
| `redacted` | Customer review when structure is useful. | Sensitive text fields are hidden. |
| `full` | Local, private runner, or customer-controlled evidence review. | Raw evidence may be present and must be controlled. |

`GITHUB_ACTIONS=true` must not produce full reports.

## PoC Deliverables

| Deliverable | Purpose | Normal audience |
|---|---|---|
| Gate Review | Main decision summary: proceed, block, review, or proceed with conditions. | Customer owner and manager |
| Gate Report / redacted report | Detailed basis for the Gate Review. | Technical reviewer |
| Safe CI summary | Automated status, pass rate, S1 failed count, and safe artifact refs. | Delivery and CI owner |
| Risk / failure pattern summary | Major risk areas and recurring failure categories. | PM and vendor lead |
| Action Items | Fixes, confirmations, owners, and due dates. | Assigned delivery owner |
| Final PoC Report | Continue, productionize, improve existing RAG, or start Proof Gate Monitor. | Decision makers |

Raw artifacts are not the normal customer decision material. Treat them as
machine-readable logs for audit or automation, and share them only when the
environment and customer agreement allow it.

## How This Connects To The Customer Template

The customer PoC repository should keep the operating materials in one place:

- `cases.csv`: agreed high-risk checks.
- `documents/`: customer-approved or sanitized source documents for local runs.
- `gate.yml`: pass/block thresholds.
- `quality-pack.yml`: pack metadata and next-action hints.
- `adapter/`: external RAG mapping when the customer already has a RAG endpoint.
- `reports/`: reviewed report exports and final summaries.
- `reviews/gate_reviews/`: Gate Reviews used as the main customer decision record.
- `reviews/investigations/`: optional cause records for BLOCK, REVIEW, or CONDITIONAL outcomes.
- `reviews/action_items/`: optional follow-up tasks.

The Gate History and machine-readable JSON remain the source of truth for
automation. Gate Review is the human-facing layer that reduces the customer's
decision burden.
