# AI Scope Sheet

## Purpose

このシートは、AI/RAG案件で「何をAIに任せるか」「何を人間確認に残すか」を、ベンダーPM・顧客責任者・技術担当が確認するための記録です。

Proof Gateは最終判断を自動化しません。このシートは、AIの利用範囲と運用条件を合意するための材料です。

## Metadata

| Item | Value |
|---|---|
| review_id |  |
| customer / project |  |
| vendor owner |  |
| customer owner |  |
| review_stage | PoC / pre_delivery / release_gate / post_delivery_change / monthly_review |
| related_gate_run_id |  |
| related_report |  |
| updated_at |  |

## AI Use Case Scope

| Item | Description |
|---|---|
| AI system name |  |
| Target users |  |
| Main tasks |  |
| Supported channels |  |
| Target document groups |  |
| Expected operating hours |  |
| Human owner |  |

## In Scope

| Scope item | Notes | Owner |
|---|---|---|
|  |  |  |
|  |  |  |
|  |  |  |

## Out of Scope

| Out-of-scope item | Reason | User-facing handling |
|---|---|---|
|  |  |  |
|  |  |  |
|  |  |  |

## Conditions for Production Use

| Condition | Required evidence or review | Status | Owner |
|---|---|---|---|
| S1/S2 blocking issues are reviewed | Gate report / ReviewPacket | not_started / in_progress / done |  |
| Customer-owned source documents are identified | Document owner confirmation | not_started / in_progress / done |  |
| Human review conditions are defined | Behavior spec / operation rule | not_started / in_progress / done |  |
| Customer submission artifact is reviewed | Safe report / customer-facing report | not_started / in_progress / done |  |

## Human Review Conditions

| Trigger | Required action | Owner | Notes |
|---|---|---|---|
| The AI cannot identify the applicable document. | Route to human review. |  |  |
| The answer affects payment, refund, contract, labor, or policy handling. | Follow the agreed escalation rule. |  |  |
| The user requests a decision outside the AI scope. | Explain the boundary and route to the owner. |  |  |
| The answer conflicts with current documents or customer instruction. | Stop release use until reviewed. |  |  |

## Customer / Vendor Confirmation

| Confirmation item | Customer owner | Vendor owner | Status | Notes |
|---|---|---|---|---|
| Scope is understood by customer owner. |  |  |  |  |
| Out-of-scope items are documented. |  |  |  |  |
| Human review conditions are documented. |  |  |  |  |
| Production use conditions are reviewed. |  |  |  |  |

## Open Questions

| Question | Owner | Due | Status |
|---|---|---|---|
|  |  |  |  |

## Notes

- Keep customer raw data in the vendor or customer-controlled environment.
- Do not paste unnecessary raw logs, personal data, source document text, or contract text into this sheet.
- Record references to artifacts instead of copying full evidence when possible.
