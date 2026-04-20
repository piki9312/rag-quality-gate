# Docs Portal

このディレクトリは、RAG Quality Gate の技術仕様と運用設計の詳細をまとめたドキュメント入口です。

製品概要と最短導入は [README.md](../README.md) を参照してください。

## 目的別に読む

初めて導入する:

- [onboarding-quickstart](demo/onboarding-quickstart.md)
- [fail-fix-cycle](demo/fail-fix-cycle.md)
- [impact-cycle](demo/impact-cycle.md)
- [packs/hr guide](../packs/hr/README.md)

コードを理解する:

- [Phase1.5 code-reading checklist](ops/getting-started/phase1-5-code-reading-checklist.md)
- [Phase2 code-reading checklist](ops/getting-started/phase2-code-reading-checklist.md)

週次運用する:

- [週次メトリクス登録](ops/operations/phase2-5-weekly-metrics-register.md)
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

1. [onboarding-quickstart](demo/onboarding-quickstart.md) で 1 回通し実行
2. [code-reading checklist](ops/getting-started/phase2-code-reading-checklist.md) で実装理解
3. [週次メトリクス](ops/operations/phase2-5-weekly-metrics-register.md) で運用開始

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

- [onboarding-quickstart](demo/onboarding-quickstart.md)
- [fail-fix-cycle](demo/fail-fix-cycle.md)
- [impact-cycle](demo/impact-cycle.md)
- [packs/hr guide](../packs/hr/README.md)

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

1. Run [onboarding-quickstart](demo/onboarding-quickstart.md) once end-to-end
2. Read [code-reading checklist](ops/getting-started/phase2-code-reading-checklist.md)
3. Start [weekly metrics](ops/operations/phase2-5-weekly-metrics-register.md)

### Notes

- See `.github/workflows/` for workflow definitions
- See `templates/` for onboarding templates
- See `demo_runs/` for execution samples