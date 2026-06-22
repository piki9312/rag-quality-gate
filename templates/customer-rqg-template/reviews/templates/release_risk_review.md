# Release Risk Review

## Purpose

このテンプレートは、Gate / ReviewPacket / review artifact の結果をもとに、本番反映・変更反映・月次確認の判断材料を整理するためのレビュー文書です。

Proof Gateは最終的な反映判断を自動化しません。リスク受容、保留、差し戻しは、顧客・ベンダーの責任者が確認してください。

## Metadata

| Item | Value |
|---|---|
| review_id |  |
| review_stage | pre_delivery / release_gate / post_delivery_change / monthly_review |
| gate_run_id |  |
| gate_report_ref |  |
| review_packet_ref |  |
| customer / project |  |
| vendor owner |  |
| customer owner |  |
| updated_at |  |

## Review Scope

| Item | Description |
|---|---|
| Target AI / RAG system |  |
| Target document corpus |  |
| Target categories |  |
| Change summary |  |
| Excluded areas |  |

## Input Artifacts

| Artifact | Reference | Notes |
|---|---|---|
| `gate-report.json` |  |  |
| `gate-decision.json` |  |  |
| ReviewPacket / Dashboard |  |  |
| `change-event.yml` |  |  |
| review artifact |  | `review.csv`, `pattern-draft-review.csv`, or `review_cases.yaml` |
| active `cases.csv` |  | Only active rows are Gate execution targets |

## Gate Result Summary

| Item | Value |
|---|---|
| Gate status | pass / conditional / fail / unknown |
| Production readiness | ready / conditional / not_ready / unknown |
| Customer submission readiness | recommended / conditional / not_recommended / unknown |
| Open S1 count |  |
| Open S2 count |  |
| Required human review | yes / no / unknown |

## S1 / S2 Risk Summary

| Severity | Category | Status | Reason | Owner | Next action |
|---|---|---|---|---|---|
| S1 |  |  |  |  |  |
| S2 |  |  |  |  |  |

## Policy / Evidence Status

| Area | Status | Reference | Notes |
|---|---|---|---|
| Source-of-truth document identified |  |  |  |
| Stale document handling defined |  |  |  |
| Change-event affected documents recorded |  |  |  |
| Case coverage for affected categories reviewed |  |  |  |
| Human review condition documented |  |  |  |

## Production Reflection Candidate Status

| Option | Candidate status | Required confirmation |
|---|---|---|
| Proceed |  |  |
| Proceed with conditions |  |  |
| Hold / rerun required |  |  |
| Out of scope for this review |  |  |

## Data / IP Boundary Open Items

| Item | Owner | Status | Notes |
|---|---|---|---|
|  |  |  |  |

## Customer / Vendor Confirmation

| Confirmation | Customer owner | Vendor owner | Status | Notes |
|---|---|---|---|---|
| Review scope is understood. |  |  |  |  |
| Open S1/S2 items are understood. |  |  |  |  |
| Human review conditions are understood. |  |  |  |  |
| Customer-facing safe report has been reviewed. |  |  |  |  |
| Residual risk, if any, is recorded by the responsible owner. |  |  |  |  |

## Next Actions

| Priority | Action | Owner | Due | Exit condition |
|---|---|---|---|---|
| High |  |  |  |  |
| Medium |  |  |  |  |

## Notes

- This review should reference Gate artifacts instead of copying raw evidence.
- Keep customer raw data in the vendor or customer-controlled environment.
- Use this file as release review material, not as an automated production approval.
