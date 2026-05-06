# ドキュメント入口

このディレクトリは、Proof Gate の技術仕様、PoC 実行手順、営業資料、運用設計をまとめた入口です。

製品概要と全体の導線は [README.md](../README.md) を参照してください。

## 顧客・営業・PoC実行者の最短導線

日本企業向けに、Proof Gate を短時間で理解したい場合は、次の順が最短です。

1. [Before / After 1枚資料](../demos/customer_support_faq_change/before_after_onepager.md)
2. [顧客提出版 Gate Report テンプレート](sales/customer_gate_report_template.md)
3. [顧客データ取扱い説明](sales/customer_data_handling_onepager.md)
4. [PoC後の選択肢: Build / Improve / Monitor](sales/post_poc_options_onepager.md)
5. [営業デモ手順](../demos/customer_support_faq_change/README.md)
6. [Proof Gate付きRAG AI導入診断PoC](user-guide/proof-gate-poc.md)

## 目的別に読む

初めて導入する:

- [Proof Gate付きRAG AI導入診断PoC](user-guide/proof-gate-poc.md)
- [簡易RAG構築と本格RAG構築の違い](sales/rag_build_scope.md)
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

- [PoC提案メモ](sales/proof-gate-poc-offer.md)
- [FAQ変更事故デモメモ](sales/customer-support-faq-change-demo.md)
- [顧客提出版 Gate Report テンプレート](sales/customer_gate_report_template.md)
- [顧客データ取扱い説明](sales/customer_data_handling_onepager.md)
- [PoC後の選択肢](sales/post_poc_options_onepager.md)

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
