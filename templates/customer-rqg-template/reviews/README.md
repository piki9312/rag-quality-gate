# Reviews

## Purpose

This `reviews/` directory is a file-based operations register for early PoC use.

The goal is not to increase review artifacts. The goal is to keep post-Gate decisions, investigations, and follow-up actions in one place.

The main artifact customers usually read is the `Gate Review`.

This directory also contains an AI案件レビューキット v0.1 for vendor PMs,
delivery leads, and customer owners. The kit is not a replacement for Gate
execution. It helps teams record the scope, behavior boundaries, data/IP
boundary, release risk, and legal review checkpoints around an AI/RAG delivery.

## Artifact Roles

| Artifact | Purpose | Audience | When to use |
|---|---|---|---|
| Gate Review | 本番反映可否を判断するための要約 | 顧客担当者・上長 | 毎回の判断時 |
| Gate Report | Gate Reviewの根拠となる詳細結果 | 技術担当・監査担当 | 詳細確認時 |
| Investigation | BLOCK/REVIEW/CONDITIONAL時の原因調査 | 技術担当・責任者 | 問題発生時のみ |
| Action Item | 修正・確認タスクの管理 | 作業担当 | 対応が必要な時 |
| FP/FN Review Log | false positive / false negative の振り返り | 技術担当・責任者 | 判定見直し時 |
| Raw artifacts | 機械可読ログ | 開発者・自動化 | 監査/自動処理時 |

## AI案件レビューキット v0.1

Use these templates before PoC review, before case creation, before production
reflection, during change review, and during monthly quality review.

| Template | Purpose | Normal owner |
|---|---|---|
| `ai_scope_sheet.md` | AI use-case scope, out-of-scope areas, production conditions, and human review conditions. | PM / Delivery Lead |
| `ai_behavior_spec.md` | Answerable boundaries, uncertainty handling, high-risk behavior, and S1/S2 linkage. | PM / QA / Tech Lead |
| `data_ip_boundary_check.md` | Customer data, vendor artifacts, safe summaries, and reusable abstract asset boundaries. | PM / Tech Lead |
| `release_risk_review.md` | Gate and ReviewPacket results converted into release risk review material. | PM / Delivery Lead |
| `legal_review_checkpoints.md` | Checkpoints for legal or contract reviewers. This is a checklist, not a legal opinion. | Legal / Contract reviewer |

Relationship to existing artifacts:

- Gate Review is the customer-facing decision summary based on Gate results.
- Investigation records cause analysis when a blocking issue appears.
- Action Item records remediation or confirmation work.
- The AI案件レビューキット records the surrounding delivery assumptions and
  review boundaries before or around those artifacts.

Filled examples:

- `examples/orbitdesk/` contains a fictional OrbitDesk FAQ RAG review example
  for PM-led customer review meetings. It uses safe summaries and artifact
  references instead of raw customer data, full evidence, or source document
  text.

## Relationship to Gate History

- `gate_history` / `gate-decision.json` / `gate-report.json` / `gate-history-summary.json` are the machine-readable source of truth.
- Gate Review does not replace `gate_history`.
- Gate Review is a human-facing decision layer based on `gate_history` and Gate Report.
- Investigation and Action Item are supporting records created only when needed.
- Each review should keep `gate_run_id` and `gate_history_ref` as metadata.

## Recommended Flow

1. Run `rqg gate`.
2. Check `gate-decision.json` / `gate-report.json` / `gate-history-summary.json`.
3. Create a Gate Review for customer decision-making.
4. Create an Investigation only for BLOCK / REVIEW / CONDITIONAL results.
5. Create an Action Item only when follow-up work is required.
6. Record false positive / false negative findings in the FP/FN review log.

## Directory Layout

```text
reviews/
  gate_reviews/
  investigations/
  action_items/
  examples/
    orbitdesk/
  templates/
    gate_review.md
    investigation.md
    action_item.md
    ai_scope_sheet.md
    ai_behavior_spec.md
    data_ip_boundary_check.md
    release_risk_review.md
    legal_review_checkpoints.md
    fp_fn_review.csv
```

## Safety Rules

- Do not write API keys or secrets.
- Do not include more customer-specific confidential information than needed.
- Anonymize and abstract records before reusing them across customers.
- Do not use raw artifacts as the main customer-facing decision artifact.
- Keep the decision in Gate Review and avoid multiplying review documents.
- Do not use these templates to make final legal, ownership, or production
  decisions automatically.
- Keep customer raw data in the vendor or customer-controlled environment.
- Record artifact references instead of copying full evidence when possible.
- Human customer/vendor/legal owners remain responsible for final review and
  acceptance decisions.

## Migration Path

- For early PoC, use Markdown files under `reviews/`.
- For continued operations or mature customers, this can move to GitHub Issues, Project Board, Jira, Linear, or Notion.
- GitHub Issues automation is a future operating option. It is not required for early PoC.
