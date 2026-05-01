# ドキュメント入口

このディレクトリは、Proof Gate の技術仕様、PoC 実行手順、営業資料、運用設計をまとめた入口です。

製品概要と全体の導線は [README.md](../README.md) を参照してください。

## 顧客・営業・PoC実行者の最短導線

日本企業向けに、Proof Gate付きRAG AI導入診断PoC の価値を短時間で理解したい場合は、次の順が最短です。

1. [Proof Gate付きRAG AI導入診断PoC](user-guide/proof-gate-poc.md)
2. [FAQ変更事故 before / afterデモ](../demos/customer_support_faq_change/README.md)
3. [PoC提案メモ](sales/customer-support-faq-change-demo.md)
4. [Customer Support Pack ガイド](../packs/customer_support_pack/README.md)

## 目的別に読む

初めて導入する:

- [Proof Gate付きRAG AI導入診断PoC](user-guide/proof-gate-poc.md)
- [onboarding-quickstart](demo/onboarding-quickstart.md)
- [fail-fix-cycle](demo/fail-fix-cycle.md)
- [impact-cycle](demo/impact-cycle.md)
- [external-contract-localhost](demo/external-contract-localhost.md) — localhost から weekly review payload まで外部契約を 1 本通す
- `rqg serve-dashboard` — pack / run / monthly summary を 1 画面で閲覧する read-only UI
- [packs/hr guide](../packs/hr/README.md)

PoC デモを見る:

- [FAQ変更事故 before / afterデモ](../demos/customer_support_faq_change/README.md)
- [Customer Support Pack ガイド](../packs/customer_support_pack/README.md)

提案・営業で使う:

- [PoC提案メモ](sales/customer-support-faq-change-demo.md)

コードを理解する:

- [Phase1.5 code-reading checklist](ops/getting-started/phase1-5-code-reading-checklist.md)
- [Phase2 code-reading checklist](ops/getting-started/phase2-code-reading-checklist.md)

週次運用する:

- [週次メトリクス登録](ops/operations/phase2-5-weekly-metrics-register.md)
- `rqg monthly-summary` — 月次の blocked run / fallback / unresolved issue を要約
- [ケース品質レビュー](ops/operations/phase2-5-case-quality-weekly-review.md)
- [失敗レビューテンプレート](ops/operations/phase2-5-ws2-failure-review-template.md)
- [ゲート例外申請テンプレート](ops/operations/phase2-5-ws3-gate-exception-approval-template.md)
- [investigate 対応フロー](ops/operations/phase2-5-investigate-response-flow.md)
- [ベースラインシート](ops/operations/phase2-5-ws1-baseline-sheet.md)
- [KPI 週次テンプレート](ops/operations/execution-template-charter-kpi-weekly.md)
- [社内文書向けパックガイド](ops/operations/phase3-internal-docs-vertical-pack.md)

過去の計画・リリース記録を確認する:

- [archive/](ops/archive/) — Phase2/2.5 のキックオフ、計画、リリースノート、完了記録

設計意図を確認する:

- [ADR: model boundaries](adr/0001-model-boundaries.md)
- [ADR: product charter and priorities](adr/0002-product-charter-and-development-priorities.md)
- [ADR: external RAG integration contract](adr/0003-external-rag-integration-contract.md)
- [ADR: evaluation status taxonomy](adr/0004-evaluation-status-taxonomy.md)
- [ADR: quality asset governance](adr/0005-quality-asset-governance.md)
- [ADR: responsibility boundary for external systems](adr/0006-responsibility-boundary-for-external-systems.md)
- [ADR: auto-generated review and merge policy](adr/0007-auto-generated-review-and-merge-policy.md)
- [ADR: RQG scope and non-goals](adr/0008-rqg-scope-and-non-goals.md)

## 用語集

→ [glossary.md](glossary.md)

## まず確認する順番

1. [Proof Gate付きRAG AI導入診断PoC](user-guide/proof-gate-poc.md) で、PoC の全体像と実行順を確認する
2. [FAQ変更事故 before / afterデモ](../demos/customer_support_faq_change/README.md) で、変更事故と改善確認の流れを把握する
3. [PoC提案メモ](sales/customer-support-faq-change-demo.md) で、顧客への説明トークを確認する
4. 外部 endpoint 境界を先に見たい場合は [external-contract-localhost](demo/external-contract-localhost.md) を使う
5. 技術理解が必要なら [code-reading checklist](ops/getting-started/phase2-code-reading-checklist.md) と [週次メトリクス](ops/operations/phase2-5-weekly-metrics-register.md) に進む

## 補足

- ワークフロー定義は `.github/workflows/` を参照
- テンプレートは `templates/` を参照
- 実行サンプルは `demo_runs/` を参照

---

## English

This directory is the documentation entry point for detailed technical and operational guidance in RAG Quality Gate.

For product overview and quick onboarding, see [README.md](../README.md).

### Browse By Goal

Getting started:

- [Vendor PoC walkthrough](demo/vendor-poc-walkthrough.md)
- [onboarding-quickstart](demo/onboarding-quickstart.md)
- [Proof Gate customer support PoC](user-guide/proof-gate-poc.md)
- [Windows PowerShell command guide](user-guide/windows-powershell.md)
- [Quality Pack S1/S2 design guide](user-guide/quality-pack-s1-s2-design.md)
- [fail-fix-cycle](demo/fail-fix-cycle.md)
- [impact-cycle](demo/impact-cycle.md)
- [external-contract-localhost](demo/external-contract-localhost.md) — run the external contract story from localhost to weekly review payload
- [packs/hr guide](../packs/hr/README.md)

Sales / proposal:

- [FAQ change sales demo draft](sales/customer-support-faq-change-demo.md)

Understanding the code:

- [Phase1.5 code-reading checklist](ops/getting-started/phase1-5-code-reading-checklist.md)
- [Phase2 code-reading checklist](ops/getting-started/phase2-code-reading-checklist.md)

Weekly operations:

- [Weekly metrics register](ops/operations/phase2-5-weekly-metrics-register.md)
- [Case quality review](ops/operations/phase2-5-case-quality-weekly-review.md)
- [Failure review template](ops/operations/phase2-5-ws2-failure-review-template.md)
- [Gate exception template](ops/operations/phase2-5-ws3-gate-exception-approval-template.md)
- [Investigate response flow](ops/operations/phase2-5-investigate-response-flow.md)
- [Baseline sheet](ops/operations/phase2-5-ws1-baseline-sheet.md)
- [KPI weekly template](ops/operations/execution-template-charter-kpi-weekly.md)
- [Internal docs pack guide](ops/operations/phase3-internal-docs-vertical-pack.md)

Product strategy:

- [Product positioning](strategy/product-positioning.md)
- [Service menu](strategy/service-menu.md)
- [GTM 0 to 10](strategy/gtm-0-to-10.md)
- [Product roadmap](roadmap/product-roadmap.md)

Past plans & release records:

- [archive/](ops/archive/) — Phase2/2.5 kickoff, plans, release notes, completion records

Architecture rationale:

- [ADR: model boundaries](adr/0001-model-boundaries.md)
- [ADR: product charter and priorities](adr/0002-product-charter-and-development-priorities.md)
- [ADR: external RAG integration contract](adr/0003-external-rag-integration-contract.md)
- [ADR: evaluation status taxonomy](adr/0004-evaluation-status-taxonomy.md)
- [ADR: quality asset governance](adr/0005-quality-asset-governance.md)
- [ADR: responsibility boundary for external systems](adr/0006-responsibility-boundary-for-external-systems.md)
- [ADR: auto-generated review and merge policy](adr/0007-auto-generated-review-and-merge-policy.md)
- [ADR: RQG scope and non-goals](adr/0008-rqg-scope-and-non-goals.md)

### Glossary

→ [glossary.md](glossary.md)

### Suggested Reading Order

1. Run [onboarding-quickstart](demo/onboarding-quickstart.md) once for the built-in path
2. If the external endpoint boundary matters first, run [external-contract-localhost](demo/external-contract-localhost.md)
3. Read [code-reading checklist](ops/getting-started/phase2-code-reading-checklist.md)
4. Start [weekly metrics](ops/operations/phase2-5-weekly-metrics-register.md)

### Notes

- See `.github/workflows/` for workflow definitions
- See `templates/` for onboarding templates
- See `demo_runs/` for execution samples
