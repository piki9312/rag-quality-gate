# Proof Gate

Proof Gate は、RAG / 顧客対応AI / FAQ AI の重大誤回答リスクを、文書変更・プロンプト変更・モデル変更の前後で検査し、リリース判断を支援する品質ゲートです。

## 30秒でわかること

- 対象: FAQ AI、顧客対応AI、社内文書検索RAG、既存チャットボット/RAG
- 提供形態: SaaS ではなく、CLI、Quality Pack、外部RAG adapter、Markdown/JSONレポートを中心にした PoC / 改善支援 / 継続監視
- 提供メニュー:
  - **Build**: Proof Gate付きRAG構築PoC
  - **Improve**: 既存RAG診断・改善PoC
  - **Monitor**: 変更後の継続品質監視
- Proof Gate は AI の安全を完全保証するものではありません。既知の高リスクケースに対する重大誤回答リスクを検査・可視化し、公開前の判断を支援します。

## 最短で見る資料

- [Before / After 1枚資料](demos/customer_support_faq_change/before_after_onepager.md)
- [顧客提出版 Gate Report テンプレート](docs/sales/customer_gate_report_template.md)
- [顧客データ取扱い説明 1枚](docs/sales/customer_data_handling_onepager.md)
- [PoC後の選択肢: Build / Improve / Monitor](docs/sales/post_poc_options_onepager.md)
- [簡易RAG構築と本格RAG構築の違い](docs/sales/rag_build_scope.md)
- [2分営業デモ台本](demos/customer_support_faq_change/sales_demo_script.md)
- [PoC / Monitor runbook](docs/user-guide/poc-monitor-runbook.md)
- [売ってよい範囲 / 約束してはいけない範囲](docs/sales/positioning-boundaries.md)
- [有償PoC readiness checklist](docs/sales/poc-readiness-checklist.md)

## 提供メニュー

### Build: Proof Gate付きRAG構築PoC

自社FAQ・規約・料金表を使って、小さくRAGを構築しながら、高リスク回答の品質診断も同時に行います。PoC後は、本格RAG構築と Proof Gate Monitor へ進みます。

### Improve: 既存RAG診断・改善PoC

既存RAG API に Proof Gate を接続し、返金・解約・料金・契約条件などの高リスク質問で品質診断を行います。PoC後は、改善支援と Proof Gate Monitor へ進みます。

### Monitor: 継続品質監視

FAQ・規約・料金表・プロンプト・モデル変更後に同じ高リスク質問セットを再実行し、重大誤回答、未解決リスク、品質劣化を継続確認します。

## PoCの簡易RAGと本格RAGの違い

| 項目 | PoCの簡易RAG構築 | 本格RAG構築 |
|---|---|---|
| 目的 | 対象文書で重大誤回答リスクを検査し、導入判断を支援する | 実運用で安定して使える顧客対応AI / 社内AIを提供する |
| 対象範囲 | 限定された FAQ・規約・料金表・ヘルプ文書 | 本番文書群、運用ルール、認証・権限・監視を含む全体 |
| 重視すること | 高リスク質問ケース、Gate判定、Before / After 比較 | UI、認証、権限、ログ、監視、SLA、運用フロー、継続評価 |
| 向いている場面 | 商談、PoC、社内稟議、改善優先度の確認 | 本番公開、運用定着、組織展開 |

> PoCの簡易RAGは本番RAGの完成版ではありません。目的は、対象文書に対してAI回答の重大リスクを検出し、導入判断に必要な論点を明らかにすることです。

## 最短の営業デモ

FAQ が v1 から v2 に変わった後も、AI が古い条件で答える変更事故を before / after で見せます。

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

見るファイル:

- `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- `demos/customer_support_faq_change/before_after_onepager.md`
- `demos/customer_support_faq_change/demo_summary.json`

このコミット済みデモで見る結論:

- before: `NG`, `policy_status=BLOCK`
- after: `OK`, `policy_status=PASS`
- after は S1 pass rate 100%、S1重大失敗 0件
- 改善後は対象文書範囲では次段階へ進める状態だが、変更リスクは残るため Monitor が必要
- evaluator fallback による `NEEDS_HUMAN_REVIEW` の説明は、固定ダッシュボードデモの review シナリオで補足できる

## ダッシュボードデモ

固定デモ artifact を作って、最小ダッシュボードで PASS / BLOCK / NEEDS_HUMAN_REVIEW の3状態を見せます。

```powershell
.\.venv\Scripts\python scripts\create_customer_support_demo_artifacts.py
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir packs\customer_support_pack\reports\demo_runs --port 8012
```

開くURL:

- `http://127.0.0.1:8012/packs`
- `http://127.0.0.1:8012/runs`
- `http://127.0.0.1:8012/cases/failures`
- `http://127.0.0.1:8012/reports/monthly`

## 通常の gate 実行

```powershell
.\.venv\Scripts\python -m rqg.cli gate --pack packs\customer_support_pack --mock --log-dir runs\customer_support_pack --reset-log-dir
```

## Evidence boundary

- Proof Gate is a **diagnostic / visibility / release-decision support layer** for high-risk RAG or chatbot answers.
- A `PASS` result means the configured checks passed for the **specified cases, documents, model, and settings** in that run.
- A `PASS` result does **not** guarantee overall production safety, legal compliance, or correctness for all user questions.
- `mock` / `ci_mock` results are **simulation only** and must not be used as evidence of production RAG quality.
- Customer-facing PoC evidence should use customer-safe artifacts such as `customer-summary.md`, not raw JSONL or mixed internal debug output.
- S1 results still require reviewed cases, grounded evidence, and manual review when the run is uncertain, simulated, or fallback-driven.

出力:

- `runs/customer_support_pack/gate-report.md`
- `runs/customer_support_pack/customer-summary.md`
- `runs/customer_support_pack/gate-decision.json`
- `runs/customer_support_pack/gate-report.json`
- `runs/customer_support_pack/gate-decisions.jsonl`
- `runs/customer_support_pack/run-provenance-<run_id>.json`

## PoC資料

- [Proof Gate PoCガイド](docs/user-guide/proof-gate-poc.md)
- [営業デモ手順](demos/customer_support_faq_change/README.md)
- [PoC提案1枚](docs/sales/proof-gate-poc-offer.md)
- [PoC後の選択肢](docs/sales/post_poc_options_onepager.md)
- [顧客データ取扱い説明](docs/sales/customer_data_handling_onepager.md)
- [Customer Support AI Quality Pack](packs/customer_support_pack/README.md)
- [既存RAG接続ガイド](docs/demo/external-rag-walkthrough.md)
- [Windows PowerShellガイド](docs/user-guide/windows-powershell.md)

## 今はやらないこと

Proof Gate は、当面は CLI、Quality Pack、外部RAG adapter、レポートを中心に整備します。SaaS、認証、課金、マルチテナント、重い管理画面は、顧客PoCで繰り返し価値が確認できるまで後回しにします。
