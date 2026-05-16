# Current Working Set

このページは、今読む・使う資料だけを集めた短い入口です。作業repoとして増えた資料を削除せず、現在の導線だけを見えるようにします。

## まず読む

- [Proof Gate Product Map](proof-gate-product-map.md) - 現時点の製品正本。
- [Product positioning](product-positioning.md) - Proof Gate が何であり、何ではないか。
- [Documentation Index](../README.md) - docs全体の置き場。
- [Logging and evidence policy](../security/logging-and-evidence-policy.md) - 顧客データ、ログ、artifact、report-mode境界。

## 顧客提出パッケージ

PoCや顧客提出物を準備するときに使います。

- [Customer gate report template](../sales/customer_gate_report_template.md)
- [Customer data handling one-pager](../sales/customer_data_handling_onepager.md)
- [Post-PoC options](../sales/post_poc_options_onepager.md)
- [Simple RAG PoC vs production RAG scope](../sales/rag_build_scope.md)
- [PoC readiness checklist](../sales/poc-readiness-checklist.md)
- [Positioning boundaries](../sales/positioning-boundaries.md)

## デモ・検証

内部で製品ストーリーを確認するときに使います。

- [FAQ change accident demo](../../demos/customer_support_faq_change/README.md)
- [Customer gate report demo](../../demos/customer_support_faq_change/customer_gate_report.md)
- [Internal S1 case authoring](../demo/internal-s1-case-authoring.md)
- [External RAG walkthrough](../demo/external-rag-walkthrough.md)
- [Windows PowerShell command guide](../user-guide/windows-powershell.md)

## 実装変更時に見る契約

挙動を変えるときに確認します。

- [External RAG adapter contract](../engineering/external-rag-adapter-contract.md)
- [Demo vs production settings](../engineering/demo-vs-production-settings.md)
- [ADR: product charter and priorities](../adr/0002-product-charter-and-development-priorities.md)
- [ADR: RQG scope and non-goals](../adr/0008-rqg-scope-and-non-goals.md)
- [ADR: CI logging and evidence policy](../adr/0009-ci-logging-and-evidence-policy.md)

## 運用に進むとき

PoCから月額運用・継続監視へ進むときだけ見ます。

- [PoC / Monitor runbook](../user-guide/poc-monitor-runbook.md)
- [Weekly metrics register](../ops/operations/phase2-5-weekly-metrics-register.md)
- [Case quality review](../ops/operations/phase2-5-case-quality-weekly-review.md)
- [Failure review template](../ops/operations/phase2-5-ws2-failure-review-template.md)
- [Gate exception template](../ops/operations/phase2-5-ws3-gate-exception-approval-template.md)

## 参考・archive扱い

有用だが、最初に読む資料ではありません。

- [Roadmap](../roadmap/product-roadmap.md)
- [GTM 0 to 10](gtm-0-to-10.md)
- [Service menu](service-menu.md)
- [Notion business drafts](notion-business/)
- [Archived Phase docs](../ops/archive/)

## 正本として扱わないもの

- `runs/`
- `demo_runs/`
- `index/`
- generated review CSV files
- 古いlocal runのgenerated report bundle
- human approval前のfailure pattern notes
