# Data / IP Boundary Check

## Purpose

このチェックシートは、AI/RAG案件で扱うデータ・成果物・再利用可能な知見の境界を整理するための確認材料です。

この文書は権利関係を確定するものではありません。必要な場合は、顧客・ベンダー・法務/契約担当が別途確認してください。

## Metadata

| Item | Value |
|---|---|
| review_id |  |
| customer / project |  |
| vendor owner |  |
| customer owner |  |
| related_scope_sheet |  |
| related_contract_or_order |  |
| updated_at |  |

## Boundary Summary

| Asset type | Normal location | Shared with Proof Gate operator? | Review owner | Notes |
|---|---|---|---|---|
| Customer FAQ / policy / contract documents | Customer or vendor-controlled environment | no by default |  |  |
| Inquiry logs | Customer or vendor-controlled environment | no by default |  |  |
| Raw AI answers | Customer or vendor-controlled environment | no by default |  |  |
| Full evidence / source paths | Customer or vendor-controlled environment | no by default |  |  |
| `cases.csv` with customer-specific expected answers | Vendor/customer-controlled artifact | no by default |  |  |
| Review artifacts | Vendor/customer-controlled artifact | no by default |  |  |
| Safe summary / aggregate metrics | Shared only when agreed | yes, bounded |  |  |
| Case Intent / Failure Pattern / test design type | Proof Gate standard asset | yes | Proof Gate asset owner | abstract only |

## Customer-Controlled Data

| Data type | Owner / controller | Storage location | Handling note |
|---|---|---|---|
| Source documents |  |  |  |
| Inquiry logs |  |  |  |
| Raw answers |  |  |  |
| Evaluation evidence |  |  |  |
| Customer-specific expected answers |  |  |  |

## Vendor / Proof Gate Asset Boundary

| Item | Treat as | Can be reused across customers? | Condition |
|---|---|---|---|
| Failure Pattern | Abstract Proof Gate asset | yes | Must not include customer raw content |
| Case Intent | Abstract Proof Gate asset | yes | Must remain customer-neutral |
| Question Variation | Abstract Proof Gate asset | yes | Must not include customer-specific facts |
| Expected Behavior Template | Abstract Proof Gate asset | yes | Must not claim customer-specific correctness |
| Review wording template | Proof Gate / vendor template | yes | Remove customer raw content |
| Customer-specific expected answer | Customer/vendor artifact | no by default | Review and approval by owner |

## Review Questions

| Question | Status | Owner | Notes |
|---|---|---|---|
| Are customer documents stored only in the agreed environment? |  |  |  |
| Are raw logs excluded from reusable templates? |  |  |  |
| Are generated expected answers treated as review candidates? |  |  |  |
| Are safe summaries bounded to category, severity, pattern, or coverage status? |  |  |  |
| Are customer-specific claims kept out of the Case Intent Library? |  |  |  |

## Open Boundary Items

| Item | Why it needs review | Owner | Due | Status |
|---|---|---|---|---|
|  |  |  |  |  |

## Notes

- Review artifacts are vendor-owned or customer-controlled artifacts unless another agreement says otherwise.
- Do not paste unnecessary customer raw data into this file.
- Use safe IDs, references, or summaries where possible.
