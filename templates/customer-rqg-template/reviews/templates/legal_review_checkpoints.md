# Legal Review Checkpoints

## Purpose

このテンプレートは、AI/RAG案件で法務・契約担当者に確認してもらう論点を整理するためのチェックリストです。

これは法務意見ではありません。Proof Gateは契約・権利・責任範囲を確定しません。必要な確認は、顧客・ベンダー・法務/契約担当が行ってください。

## Metadata

| Item | Value |
|---|---|
| review_id |  |
| customer / project |  |
| vendor owner |  |
| legal / contract reviewer |  |
| related_scope_sheet |  |
| related_data_boundary_check |  |
| updated_at |  |

## Checkpoints

| Area | Review question | Status | Owner | Notes |
|---|---|---|---|---|
| Contract form | Is the applicable contract / order / statement of work identified? |  |  |  |
| Deliverables | Are delivery artifacts and non-deliverables described clearly enough for review? |  |  |  |
| Customer data | Are customer documents, logs, and full evidence handled in the agreed environment? |  |  |  |
| Log storage | Is storage, retention, and access for logs documented? |  |  |  |
| Training / improvement use | Is any use of customer data for improvement explicitly reviewed? |  |  |  |
| Evaluation cases | Are customer-specific expected answers treated as customer/vendor-controlled artifacts? |  |  |  |
| Templates / patterns | Are abstract templates and failure patterns separated from customer raw content? |  |  |  |
| Vendor existing assets | Are pre-existing vendor or Proof Gate assets distinguished from customer-specific artifacts? |  |  |  |
| Customer customization | Are custom prompts, cases, or documents identified as project-specific artifacts? |  |  |  |
| Exclusivity / reuse | Are reuse boundaries for abstract know-how and customer-specific materials reviewed? |  |  |  |
| Liability scope | Are escalation and human review conditions documented for high-risk answers? |  |  |  |

## Data / Artifact Classification

| Artifact | Candidate classification | Reviewer note |
|---|---|---|
| Customer source documents | Customer-controlled |  |
| Raw inquiry logs | Customer-controlled |  |
| Raw AI answers and full evidence | Customer/vendor-controlled |  |
| Customer-specific `cases.csv` | Customer/vendor-controlled |  |
| Review artifacts | Vendor-owned or customer-controlled |  |
| Case Intent / Failure Pattern | Abstract Proof Gate/vendor asset |  |
| Report template | Template asset |  |

## Items Needing Follow-Up

| Item | Why it needs review | Owner | Due | Status |
|---|---|---|---|---|
|  |  |  |  |  |

## Notes

- Do not paste unnecessary customer raw data or contract text into this checklist.
- Link to controlled artifacts where needed.
- Final handling should be recorded by the responsible customer/vendor/legal owner.
