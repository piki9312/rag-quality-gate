# Customer Support FAQ変更事故デモ

この資料は、Proof Gate付き RAG AI導入診断PoCを営業・提案時に説明するためのメモです。

## 伝えること

FAQ・規約・料金表が変わった後、RAG AI が古い条件で自然に答えてしまうことがあります。Proof Gate は、本番反映前に高リスク質問をまとめて確認し、S1重大失敗を検知して止めます。

このデモでは、FAQ v1 では危険な回答が出る状態を before、FAQ v2 に修正した後に同じケースで改善する状態を after として見せます。

## 統一した判定

| 観点 | Before | After |
|---|---:|---:|
| 顧客向け結論 | 本番反映不可 | 本番反映可 |
| 本番反映判定 | `NG` | `OK` |
| policy_status | `BLOCK` | `PASS` |
| overall_decision | `ng` | `ok` |
| S1 pass rate | 0.0% | 100.0% |
| overall pass rate | 16.7% | 100.0% |
| S1重大失敗 | 3件 | 0件 |
| 人手確認要否 | 不要。本番反映を止める判断 | 不要 |

## 使用ファイル

- デモ一式: `demos/customer_support_faq_change/`
- 1枚比較: `demos/customer_support_faq_change/before_after_onepager.md`
- 顧客提出版レポート: `demos/customer_support_faq_change/customer_gate_report.md`
- before report: `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- after report: `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- 要約JSON: `demos/customer_support_faq_change/demo_summary.json`

## 実行

```powershell
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

## 話す順番

### Before

1. `before_after_onepager.md` で全体像を見せる。
2. beforeは `NG` / `policy_status=BLOCK` で、本番反映不可と説明する。
3. S1重大失敗が3件あり、返金・解約・契約条件で古いFAQ条件の回答が残っていたと説明する。
4. 必要に応じて `reports/before_stale_v1/gate-report.md` の詳細を開く。

### After

1. afterは `OK` / `policy_status=PASS` / `overall_decision=ok` と説明する。
2. S1 pass rate 100.0%、S1重大失敗0件、human review不要であることを見せる。
3. 「同じ高リスク質問セットで再確認し、改善を証明できる」と説明する。
4. 必要に応じて `reports/after_v2_reference/gate-report.md` の詳細を開く。

### Closing

`customer_gate_report.md` を見せて、PoC後の提案へつなげます。

- FAQ・規約・料金表・プロンプト変更は継続的に起きる。
- 一度通ったAIでも、変更後に危険な回答へ戻ることがある。
- PoC後は、本格RAG構築、既存RAG改善支援、Proof Gate Monitor のいずれかを選ぶ。

## 顧客向け一言

Proof Gate は、RAGを置き換えるものではありません。RAG AIの更新や運用の前後に、高リスク質問を再確認し、危険な回答を本番前に止めるための品質ゲートです。

PoC用の簡易RAGは診断と説明のための軽量構成です。本番RAGに進む場合は、顧客環境、セキュリティ、監視、改善サイクルを含む本格構築として別途設計します。
