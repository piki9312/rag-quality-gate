# OrbitDesk FAQ RAG Review Example

## Purpose

This example shows how a vendor PM might fill the AI案件レビューキット v0.1
for a fictional FAQ RAG delivery project.

The project is:

- Customer: OrbitDesk株式会社
- Vendor: Example AI Vendor
- Project: OrbitDesk FAQ RAG導入支援
- Target AI: FAQ RAG chatbot
- Current phase: 本番反映前レビュー
- Review audience: customer owner, vendor PM, QA lead, and technical owner

## Included Samples

| File | Template shown |
|---|---|
| `ai_scope_sheet.sample.md` | AI利用範囲、対象外、運用条件、人間確認条件 |
| `ai_behavior_spec.sample.md` | 回答方針、回答禁止領域、不明時挙動、重大リスク |
| `data_ip_boundary_check.sample.md` | 顧客データ、評価ケース、テンプレート、再利用範囲の確認 |
| `release_risk_review.sample.md` | Gate結果を使った本番反映前のリスクレビュー材料 |
| `legal_review_checkpoints.sample.md` | 法務・契約担当に確認する論点リスト |

## How to Read

The sample is written as material a vendor PM can bring to a customer review
meeting. It does not include raw customer data, full evidence, source document
text, inquiry logs, or contract text.

Use the sample as a structure for:

- decision materials
- review evidence records
- unresolved issue tracking
- customer/vendor confirmation items
- safe summary and artifact references

## Safety Notes

- Proof Gate does not make contract, IP, liability, or production release
  decisions.
- Proof Gate does not turn generated answers into formal customer-specific
  answers without vendor/customer review.
- `review.csv`, `pattern-draft-review.csv`, and `review_cases.yaml` are review
  candidate artifacts, not formal `cases.csv`.
- Only vendor/customer-approved active `cases.csv` rows are Gate execution
  targets.
- Keep customer raw data and full evidence in the vendor or customer-controlled
  environment.

## Fictional Artifact References

| Artifact | Reference |
|---|---|
| Gate report | `artifacts/orbitdesk/2026-06-pre-release/gate-report.json` |
| ReviewPacket / dashboard | `artifacts/orbitdesk/2026-06-pre-release/review-packet.json` |
| Review candidate artifact | `reviews/orbitdesk/review_cases.yaml` |
| Active cases | `packs/orbitdesk/cases.csv` |
| Change event | `reviews/orbitdesk/change-event.yml` |
