# Proof Gate

Proof Gate は、RAG や顧客対応AI / FAQ AI の重大誤回答リスクを、文書変更・プロンプト変更・モデル変更の前後で検査し、顧客提出用レポートまで揃えて本番判断と継続監視を支援する Release Gate です。

現時点の提供形態は SaaS ではなく、CLI、Quality Pack、外部RAG adapter、Markdown/JSONレポート、顧客向けPoC成果物を中心にした PoC / 改善支援 / 継続監視です。RAGエンジンそのものを置き換えるのではなく、既存または新規の RAG / FAQ AI の外側に品質ゲートを置きます。

## まず見る

- [Product Map](docs/strategy/proof-gate-product-map.md) - 事業目的、対象範囲、現在の実装、やらないこと。
- [Current Working Set](docs/strategy/current-working-set.md) - 今読む・使う資料だけを集めた入口。
- [Documentation Index](docs/README.md) - docs全体を営業、デモ、技術、運用、archiveに分けた入口。

## 概要

- 対象: FAQ AI、顧客対応AI、社内文書検索RAG、既存チャットボット / RAG
- 提供形態: CLI、Quality Pack、外部RAG adapter、Markdown/JSONレポート、顧客向けPoC成果物を中心にした PoC / 改善支援 / 継続監視
- 提供メニュー:
  - **Build**: Proof Gate付きRAG構築PoC
  - **Improve**: 既存RAG診断・改善PoC
  - **Monitor**: 変更後の継続品質監視
- Proof Gate は AI の安全を完全保証するものではありません。既知の高リスクケースに対する重大誤回答リスクを検査・可視化し、公開前の判断を支援します。

## 解決する課題

RAG AI は、FAQ・規約・料金表・社内ルールが変わった後も、古い条件で自然に答えてしまうことがあります。特に返金、解約、料金、契約条件、期限、資格条件の誤回答は、顧客対応事故や社内説明責任につながります。

Proof Gate は、こうした高リスク質問を `cases.csv` として管理し、RAG AI の回答をリリース前または定期運用で再チェックします。

## Proof Gate がやること

- S1重大失敗を検知し、本番反映を止める判断材料を出す。
- S2品質課題として、文書網羅、検索、説明品質の劣化を確認する。
- mock、local、external RAG endpoint に対して同じQuality Packを実行する。
- `gate-decision.json`、`gate-report.json`、`gate-report.md`、顧客向けsummaryを出す。
- Build / Improve / Monitor の提供メニューに接続する。

## 顧客提出・営業でまず使う資料

- [Before / After one-pager](demos/customer_support_faq_change/before_after_onepager.md)
- [2分営業デモ台本](demos/customer_support_faq_change/sales_demo_script.md)
- [Customer gate report](demos/customer_support_faq_change/customer_gate_report.md)
- [Customer gate report template](docs/sales/customer_gate_report_template.md)
- [Customer data handling one-pager](docs/sales/customer_data_handling_onepager.md)
- [Post-PoC options](docs/sales/post_poc_options_onepager.md)
- [Proof Gate next offer](docs/sales/proof-gate-next-offer.md)
- [Simple RAG PoC vs production RAG scope](docs/sales/rag_build_scope.md)
- [Positioning boundaries](docs/sales/positioning-boundaries.md)
- [PoC / Monitor runbook](docs/user-guide/poc-monitor-runbook.md)
- [PoC readiness checklist](docs/sales/poc-readiness-checklist.md)

## PoCの簡易RAGと本格RAGの違い

| 項目 | PoCの簡易RAG構築 | 本格RAG構築 |
|---|---|---|
| 目的 | 対象文書で重大誤回答リスクを検査し、導入判断を支援する | 実運用で安定して使える顧客対応AI / 社内AIを提供する |
| 対象範囲 | 限定された FAQ・規約・料金表・ヘルプ文書 | 本番文書群、運用ルール、認証・権限・監視を含む全体 |
| 重視すること | 高リスク質問ケース、Gate判定、Before / After 比較 | UI、認証、権限、ログ、監視、SLA、運用フロー、継続評価 |
| 向いている場面 | 商談、PoC、社内稟議、改善優先度の確認 | 本番公開、運用定着、組織展開 |

> PoCの簡易RAGは本番RAGの完成版ではありません。目的は、対象文書に対してAI回答の重大リスクを検出し、導入判断に必要な論点を明らかにすることです。

## デモとローカル実行

### FAQ変更事故デモを再生成する

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

### Customer Support Pack で gate を実行する

```powershell
.\.venv\Scripts\python -m rqg.cli gate --pack packs\customer_support_pack --mock --log-dir runs\customer_support_pack --reset-log-dir
```

### read-only dashboard demo を開く

```powershell
.\.venv\Scripts\python scripts\create_customer_support_demo_artifacts.py
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir packs\customer_support_pack\reports\demo_runs --port 8012
```

### 変更後リリースレビュー demo を開く

```powershell
.\.venv\Scripts\python -m rqg.cli validate-pack --pack packs\release_review_demo --strict-s1-governance
.\.venv\Scripts\python -m rqg.cli gate --pack packs\release_review_demo --mock --change-event packs\release_review_demo\change-event.yml --index-dir index\release_review_demo --log-dir demo_runs\release_review_demo --reset-log-dir
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir demo_runs\release_review_demo --port 8012
```

## `change-event.yml` で変更後レビューを明示する

`change-event.yml` は、FAQ / 規約 / 料金表 / プロンプト / モデル / retriever 設定など、今回何を変えたかを `rqg gate` / `rqg check` に安定して渡すための最小入力です。変更後リリースレビューで、再テスト範囲と production readiness の文脈を揃えたいときに使います。

使うタイミング:

- FAQ 更新
- 規約変更
- 料金表変更
- プロンプト変更
- モデル変更
- retriever 設定変更

安全なサンプルは [templates/change-event.example.yml](templates/change-event.example.yml) から始めてください。

実行例:

```powershell
.\.venv\Scripts\python -m rqg.cli gate --pack packs\customer_support_pack --mock --change-event change-event.yml --log-dir runs\customer_support_pack --reset-log-dir
.\.venv\Scripts\python -m rqg.cli check --log-dir runs\customer_support_pack --change-event change-event.yml
```

Dashboard / review で見えるもの:

- Run Detail の Change Event Card
- Production Readiness Card / warning
- Report Preview の Change Summary

## Evidence Boundary

safe / full の注意:

- CI-safe artifact には raw asset name / raw document name / path / target_release / customer-specific summary を出しません。
- full metadata は local / private runner / customer-controlled 環境だけで扱います。
- `change-event.yml` 自体にも機密情報を書きすぎず、入力時点で最小情報にしてください。
- safe 版では hash / count / bounded metadata だけを出します。
- sanitizer に頼るのではなく、入力時点で customer-specific 情報を減らしてください。

主な出力と注意事項:

- `PASS` は、そのrunで指定されたケース、文書、モデル、設定に対してチェックを通過したという意味です。
- `PASS` は、全質問に対する本番安全性、法令適合性、完全な正確性を保証しません。
- `mock` / `ci_mock` はシミュレーションであり、本番RAG品質の証跡には使いません。
- 顧客提出では、raw JSONL、full debug output、vector index、内部ログを使わず、customer-safe artifact を使います。
- S1ケースは、業務リスク、文書根拠、expected answer、block reason、人間承認を前提にします。

詳細は [Logging and Evidence Policy](docs/security/logging-and-evidence-policy.md) を参照してください。

## 追加資料

- [営業デモ手順](demos/customer_support_faq_change/README.md)
- [営業デモ説明メモ](docs/sales/customer-support-faq-change-demo.md)
- [PoC提案1枚](docs/sales/proof-gate-poc-offer.md)
- [Proof Gate PoCガイド](docs/user-guide/proof-gate-poc.md)
- [Customer Support AI Quality Pack](packs/customer_support_pack/README.md)
- [既存RAG接続ガイド](docs/demo/external-rag-walkthrough.md)
- [Windows PowerShellガイド](docs/user-guide/windows-powershell.md)

## 今はやらないこと

Proof Gate は当面、CLI、Quality Pack、外部RAG adapter、レポート、PoC成果物を中心に整備します。SaaS、認証、課金、tenant管理、asset registry、重い管理画面は、複数の有償PoCで繰り返し価値が確認できるまで後回しにします。
