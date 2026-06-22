# AI Behavior Spec

## Purpose

このテンプレートは、AI/RAGが「どう答えるべきか」「答えてはいけない場合にどう扱うか」を整理するためのレビュー材料です。

これは運用上の期待動作を整理する文書であり、Proof Gateが顧客固有の正解や最終判断を確定するものではありません。

## Metadata

| Item | Value |
|---|---|
| review_id |  |
| customer / project |  |
| system name |  |
| related_scope_sheet |  |
| related_gate_run_id |  |
| updated_at |  |

## Answerable Areas

| Area | Answer condition | Required source type | Human owner |
|---|---|---|---|
|  |  |  |  |
|  |  |  |  |

## Not-Answerable Areas

| Area | Why AI should not answer directly | Required user-facing handling |
|---|---|---|
|  |  |  |
|  |  |  |

## Uncertainty Handling

| Situation | Expected behavior | Escalation owner |
|---|---|---|
| Source document is missing. | State that the answer cannot be confirmed from available sources and route to review. |  |
| Multiple documents conflict. | Do not choose a rule automatically. Route to the agreed owner. |  |
| User asks for a decision outside scope. | Explain the boundary and provide the next contact path. |  |
| The AI answer would affect high-risk handling. | Follow the human review condition. |  |

## High-Risk Domains

| Domain | Risk reason | Linked severity | Required behavior |
|---|---|---|---|
| refund | Financial and customer trust impact | S1 / S2 |  |
| cancellation | Contract and customer handling impact | S1 / S2 |  |
| pricing | Commercial impact | S1 / S2 |  |
| labor / HR | Employee policy impact | S1 / S2 |  |
| legal / contract | Requires responsible review | S1 / S2 |  |

## Expected Behavior Patterns

| Pattern | Expected behavior template | Notes marker |
|---|---|---|
| Evidence required | Cite or refer to the applicable approved source type. | design:evidence_required |
| Human review required | Route to the responsible reviewer when the answer crosses the agreed boundary. | release:needs_human_review |
| Stale reference risk | Prefer current effective rules and flag uncertainty when version is unclear. | design:stale_reference |
| Business rule boundary | Avoid extending a rule beyond the written source. | design:boundary_value |

## S1 / S2 Linkage

| Risk | Linked cases or intents | Expected handling | Owner |
|---|---|---|---|
|  |  |  |  |

## Review Checklist

- [ ] Answerable areas are listed.
- [ ] Not-answerable areas are listed.
- [ ] Uncertainty handling is defined.
- [ ] High-risk domains are mapped to S1/S2 review.
- [ ] Human review conditions are consistent with the AI Scope Sheet.
- [ ] Customer-specific expected answers are reviewed by the vendor/customer owner before active use.

## Notes

- Do not paste customer raw logs or source document text unless the environment is controlled for that use.
- Use artifact references, case IDs, or safe summaries when possible.
