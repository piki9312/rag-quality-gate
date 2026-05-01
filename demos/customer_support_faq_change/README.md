# カスタマーサポートFAQ変更事故デモ

このディレクトリは、Proof Gate付きRAG AI導入診断PoCを営業や顧客説明で短時間に見せるためのデモ一式です。

## 最短の営業デモ手順

2分で説明したい場合は、次の順番で見せます。

1. デモartifactを再生成する。
2. before report を開き、本番反映判定が止まっていることを見せる。
3. after report を開き、同じ高リスク質問で改善したことを見せる。
4. 比較メモと `demo_summary.json` を使って、月額Monitorによる継続監視の必要性まで説明する。

実行コマンド:

```powershell
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

開く順番のファイル:

- `demos/customer_support_faq_change/sales_demo_script.md`
- `demos/customer_support_faq_change/before_after_onepager.md`
- `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- `demos/customer_support_faq_change/demo_summary.json`

before report で見る場所:

- `1. 本番反映判定`: `NG` と `policy_status: BLOCK` を見せる。
- `4. 実行結果サマリ`: `overall_pass_rate: 33.3%` と `s1_pass_rate: 0.0%` を見せる。
- `5. S1重大失敗一覧`: 返金・解約に関する高リスク質問が失敗していることを見せる。
- `8. 月額Monitorで継続確認すべき項目`: 継続監視が必要な理由につなげる。

after report で見る場所:

- `1. 本番反映判定`: `OK` と `policy_status: PASS` を見せる。
- `4. 実行結果サマリ`: `overall_pass_rate: 100.0%` と `s1_pass_rate: 100.0%` を見せる。
- `5. S1重大失敗一覧`: 重大失敗が解消していることを確認する。

`demo_summary.json` の意味:

- `before`: 古いFAQ v1で回答してしまうため、止めるべき状態の結果。
- `after`: FAQ v2で再判定した結果で、通過すべき状態の結果。
- `representative_s1_failure`: 会議で説明しやすい代表的なS1重大失敗。
- `key_message`: 最後に一言で伝える営業メッセージ。

## ディレクトリ構成

- `demo_faq_v1.md` / `demo_faq_v2.md`: 変更前と変更後のFAQ本文。
- `generated_cases.csv`: デモ用に選んだ高リスク質問の元データ。
- `cases.csv`: 実際に評価で使うケースセット。
- `case_set_summary.json`: ケースセットの件数と内訳をまとめた要約。
- `reports/before_stale_v1/`: 古いFAQ参照のまま評価した before artifact。
- `reports/after_v2_reference/`: 更新後FAQで再評価した after artifact。
- `demo_summary.json`: before / after を1つにまとめた比較要約。

## このデモで伝えること

- before では、RAG AIが古いFAQ v1のまま答え、返金・解約・料金・契約条件の説明で変更事故が起きる。
- Proof Gateは、その回答をS1重大失敗として検知し、本番反映判定を `NG` にする。
- after では、同じ高リスク質問セットをFAQ v2で再実行し、改善を確認する。
- 月額Monitorで継続監視することで、FAQ・規約・プロンプト変更のあとも再発を防ぎやすくなる。

## 実行方法

リポジトリのルートで次を実行します。

```powershell
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

更新されるartifact:

- `demos/customer_support_faq_change/generated_cases.csv`
- `demos/customer_support_faq_change/cases.csv`
- `demos/customer_support_faq_change/case_set_summary.json`
- `demos/customer_support_faq_change/reports/before_stale_v1/`
- `demos/customer_support_faq_change/reports/after_v2_reference/`
- `demos/customer_support_faq_change/demo_summary.json`

## 営業時に見せる順番

1. `reports/before_stale_v1/gate-report.md` を開き、`1. 本番反映判定` と `5. S1重大失敗一覧` を最初に見せる。
2. `購入から7日以内なら返金できますか？` が旧v1ルールのまま答えられていることを説明する。
3. `reports/after_v2_reference/gate-report.md` を開き、同じ高リスク質問セットで改善したことを見せる。
4. `demo_summary.json` を開き、before / after の pass rate と S1重大失敗件数を比較する。

## 営業用補助資料

- `sales_demo_script.md`: 2分営業トークをそのまま読める台本。
- `before_after_onepager.md`: before / after を1枚で比較する説明メモ。

## レポートの読み方

- before では、`1. 本番反映判定`、`4. 実行結果サマリ`、`5. S1重大失敗一覧` を中心に見る。
- after では、同じ場所を見て、S1重大失敗が解消していることを確認する。
- レポート上部は営業・顧客向けの説明に使いやすく、下部の `運用向け詳細` は技術確認や運用説明に使う。