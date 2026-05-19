# Documentation Index

このディレクトリは、Proof Gate のドキュメント入口です。現在のrepoは作業リポジトリでもあるため、資料を「正本」「顧客向け」「デモ」「技術契約」「運用」「archive」に分けて読む前提にします。

短い製品入口は [README.md](../README.md) を参照してください。

## まず読む

1. [Proof Gate Product Map](strategy/proof-gate-product-map.md) - 事業目的、対象範囲、現在の実装、やらないこと。
2. [Current Working Set](strategy/current-working-set.md) - 今読む・使う資料だけを集めた入口。
3. [Product positioning](strategy/product-positioning.md) - Proof Gate が何であり、何ではないか。
4. [Logging and evidence policy](security/logging-and-evidence-policy.md) - 顧客データ、ログ、artifact、report-modeの境界。

## 顧客向け・営業

- [PoC offer](sales/proof-gate-poc-offer.md)
- [PoC security and deliverables summary](sales/proof-gate-poc-security-and-deliverables.md)
- [Customer gate report template](sales/customer_gate_report_template.md)
- [Customer data handling one-pager](sales/customer_data_handling_onepager.md)
- [Post-PoC options](sales/post_poc_options_onepager.md)
- [After-PoC offer](sales/proof-gate-next-offer.md)
- [Simple RAG PoC vs production RAG scope](sales/rag_build_scope.md)
- [Positioning boundaries](sales/positioning-boundaries.md)
- [PoC readiness checklist](sales/poc-readiness-checklist.md)
- [FAQ change sales demo memo](sales/customer-support-faq-change-demo.md)

## デモ・内部検証

- [FAQ change accident demo](../demos/customer_support_faq_change/README.md)
- [Internal S1 case authoring](demo/internal-s1-case-authoring.md)
- [Onboarding quickstart](demo/onboarding-quickstart.md)
- [Fail-fix cycle](demo/fail-fix-cycle.md)
- [Impact cycle](demo/impact-cycle.md)
- [External RAG walkthrough](demo/external-rag-walkthrough.md)
- [External contract localhost](demo/external-contract-localhost.md)
- [External real PoC runbook](demo/external-real-poc-runbook.md)

## 利用ガイド

- [Proof Gate PoC guide](user-guide/proof-gate-poc.md)
- [PoC / Monitor runbook](user-guide/poc-monitor-runbook.md)
- [Quality Pack S1/S2 design guide](user-guide/quality-pack-s1-s2-design.md)
- [Windows PowerShell command guide](user-guide/windows-powershell.md)

## 技術契約・設計意図

- [External RAG adapter contract](engineering/external-rag-adapter-contract.md)
- [Demo vs production settings](engineering/demo-vs-production-settings.md)
- [ADR: model boundaries](adr/0001-model-boundaries.md)
- [ADR: product charter and priorities](adr/0002-product-charter-and-development-priorities.md)
- [ADR: external RAG integration contract](adr/0003-external-rag-integration-contract.md)
- [ADR: evaluation status taxonomy](adr/0004-evaluation-status-taxonomy.md)
- [ADR: quality asset governance](adr/0005-quality-asset-governance.md)
- [ADR: responsibility boundary for external systems](adr/0006-responsibility-boundary-for-external-systems.md)
- [ADR: auto-generated review and merge policy](adr/0007-auto-generated-review-and-merge-policy.md)
- [ADR: RQG scope and non-goals](adr/0008-rqg-scope-and-non-goals.md)
- [ADR: CI logging and evidence policy](adr/0009-ci-logging-and-evidence-policy.md)

## 運用

PoCから月額監視や内部dogfoodingへ進むときに使います。

- [Weekly metrics register](ops/operations/phase2-5-weekly-metrics-register.md)
- [Case quality review](ops/operations/phase2-5-case-quality-weekly-review.md)
- [Failure review template](ops/operations/phase2-5-ws2-failure-review-template.md)
- [Gate exception template](ops/operations/phase2-5-ws3-gate-exception-approval-template.md)
- [Investigate response flow](ops/operations/phase2-5-investigate-response-flow.md)
- [Baseline sheet](ops/operations/phase2-5-ws1-baseline-sheet.md)
- [KPI weekly template](ops/operations/execution-template-charter-kpi-weekly.md)
- [Internal docs pack guide](ops/operations/phase3-internal-docs-vertical-pack.md)

## Archive・作業メモ

過去Phaseの計画、dogfooding記録、古い読解メモは履歴として扱います。必要なときだけ参照し、現在の導線とは分けます。

- [Archive](ops/archive/)
- [Phase1.5 code-reading checklist](ops/getting-started/phase1-5-code-reading-checklist.md)
- [Phase2 code-reading checklist](ops/getting-started/phase2-code-reading-checklist.md)
- [Notion business drafts](strategy/notion-business/)

## Reference

- [Glossary](glossary.md)
- Workflow definitions: [../.github/workflows/](../.github/workflows/)
- GitHub templates: [../templates/github/](../templates/github/)
- Sample pack template: [../templates/sample_pack/](../templates/sample_pack/)
- Demo artifacts: [../demos/](../demos/)
