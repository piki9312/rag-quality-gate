# Proof Gate

Proof Gate は、RAG / AIチャットボットの導入・納品・変更運用に対して、重大誤回答の有無を検査し、顧客提出用レポートまで揃えて本番判断を支援する Release Gate です。

現時点の提供形態は SaaS ではなく、CLI、Quality Pack、外部RAG adapter、Markdown/JSONレポート、顧客向けPoC成果物を中心にします。RAGエンジンそのものを置き換えるのではなく、既存または新規の RAG / FAQ AI の外側に品質ゲートを置きます。

## まず見る

- [Product Map](docs/strategy/proof-gate-product-map.md) - 事業目的、対象範囲、現在の実装、やらないこと。
- [Current Working Set](docs/strategy/current-working-set.md) - 今読む・使う資料だけを集めた入口。
- [Documentation Index](docs/README.md) - docs全体を営業、デモ、技術、運用、archiveに分けた入口。

## Proof Gate がやること

- S1重大失敗を検知し、本番反映を止める判断材料を出す。
- S2品質課題として、文書網羅、検索、説明品質の劣化を確認する。
- mock、local、external RAG endpoint に対して同じQuality Packを実行する。
- `gate-decision.json`、`gate-report.json`、`gate-report.md`、顧客向けsummaryを出す。
- Build / Improve / Monitor の提供メニューに接続する。

## 顧客提出・営業で使う資料

- [Before / After one-pager](demos/customer_support_faq_change/before_after_onepager.md)
- [Customer gate report](demos/customer_support_faq_change/customer_gate_report.md)
- [Customer gate report template](docs/sales/customer_gate_report_template.md)
- [Customer data handling one-pager](docs/sales/customer_data_handling_onepager.md)
- [Post-PoC options](docs/sales/post_poc_options_onepager.md)
- [Simple RAG PoC vs production RAG scope](docs/sales/rag_build_scope.md)
- [Positioning boundaries](docs/sales/positioning-boundaries.md)
- [PoC readiness checklist](docs/sales/poc-readiness-checklist.md)

## デモとローカル実行

FAQ変更事故デモを再生成する:

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

Customer Support Pack でgateを実行する:

```powershell
.\.venv\Scripts\python -m rqg.cli gate --pack packs\customer_support_pack --mock --log-dir runs\customer_support_pack --reset-log-dir
```

read-only dashboard demoを開く:

```powershell
.\.venv\Scripts\python scripts\create_customer_support_demo_artifacts.py
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir packs\customer_support_pack\reports\demo_runs --port 8012
```

## Evidence Boundary

- `PASS` は、そのrunで指定されたケース、文書、モデル、設定に対してチェックを通過したという意味です。
- `PASS` は、全質問に対する本番安全性、法令適合性、完全な正確性を保証しません。
- `mock` / `ci_mock` はシミュレーションであり、本番RAG品質の証跡には使いません。
- 顧客提出では、raw JSONL、full debug output、vector index、内部ログを使わず、customer-safe artifactを使います。
- S1ケースは、業務リスク、文書根拠、expected answer、block reason、人間承認を前提にします。

詳細は [Logging and Evidence Policy](docs/security/logging-and-evidence-policy.md) を参照してください。

## 今はやらないこと

Proof Gate は当面、CLI、Quality Pack、外部RAG adapter、レポート、PoC成果物を中心に整備します。SaaS、認証、課金、tenant管理、asset registry、重い管理画面は、複数の有償PoCで繰り返し価値が確認できるまで後回しにします。
