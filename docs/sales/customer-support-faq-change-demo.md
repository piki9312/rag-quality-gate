# Customer Support FAQ変更事故デモ

この資料は、Proof Gate付き RAG AI導入診断PoCを営業・提案時に説明するためのメモです。

## 伝えること

FAQ・規約・料金表が変わった後、RAG AI が古い条件で自然に答えてしまうことがあります。Proof Gate は、本番反映前に高リスク質問をまとめて確認し、S1重大失敗を検知して止めます。

このデモでは、FAQ v1 では危険な回答が出る状態を before、FAQ v2 に修正した後に同じケースで改善する状態を after として見せます。

## 使用ファイル

- デモ一式: `demos/customer_support_faq_change/`
- before report: `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- after report: `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- 比較メモ: `demos/customer_support_faq_change/before_after_onepager.md`
- 要約JSON: `demos/customer_support_faq_change/demo_summary.json`

## 実行

```powershell
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

## 話す順番

### Before

1. `reports/before_stale_v1/gate-report.md` を開く。
2. `1. 本番反映判定` で `NG` と `policy_status: BLOCK` を見せる。
3. `5. S1重大失敗一覧` で、返金・解約・料金・契約条件などの高リスク質問が失敗していることを見せる。
4. 「AIの文章は自然でも、現在のFAQ条件とは違う回答をしている」と説明する。

### After

1. `reports/after_v2_reference/gate-report.md` を開く。
2. `1. 本番反映判定` で `要確認` と `policy_status: NEEDS_HUMAN_REVIEW` を見せる。
3. `4. 実行結果サマリ` で S1 pass rate と overall pass rate の改善、S1重大失敗の解消を見せる。
4. ローカルfallbackがあるため人手確認扱いだが、beforeの `BLOCK` から安全側に改善したことを説明する。
5. 「同じ高リスク質問セットで再確認し、改善を証明できる」と説明する。

### Closing

`before_after_onepager.md` または `demo_summary.json` を見せて、月額Monitorへつなげます。

月額Monitorの説明:

- FAQ・規約・料金表・プロンプト変更は継続的に起きる。
- 一度通ったAIでも、変更後に危険な回答へ戻ることがある。
- 高リスク質問を定期実行し、S1重大失敗と未解決リスクを継続確認する。

## 顧客向け一言

Proof Gate は、RAGを置き換えるものではありません。RAG AIの更新や運用の前後に、高リスク質問を再確認し、危険な回答を本番前に止めるための品質ゲートです。
