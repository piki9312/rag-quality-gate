# Customer Support FAQ変更事故デモ

このディレクトリは、Proof Gate付き RAG AI導入診断PoCを短時間で見せるための before / after 営業デモです。

## デモの結論

| 観点 | Before | After |
|---|---:|---:|
| 本番反映判定 | `NG` | `OK` |
| policy_status | `BLOCK` | `PASS` |
| overall_decision | `ng` | `ok` |
| S1 pass rate | 0.0% | 100.0% |
| S1重大失敗 | 3件 | 0件 |
| 人手確認要否 | 不要。本番反映を止める判断 | 不要 |

Beforeでは、FAQ v1 の古い条件に基づく回答を S1重大失敗として検知します。Afterでは、FAQ v2 に修正した後、同じ高リスク質問セットで `policy_status=PASS` になります。

## 最短手順

```powershell
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

生成後、次の順で開きます。

1. `sales_demo_script.md`
2. `before_after_onepager.md`
3. `customer_gate_report.md`
4. `reports/before_stale_v1/gate-report.md`
5. `reports/after_v2_reference/gate-report.md`
6. `demo_summary.json`

## ディレクトリ構成

- `demo_faq_v1.md`: before用の古いFAQ
- `demo_faq_v2.md`: after用の更新済みFAQ
- `generated_cases.csv`: デモ用に選んだ高リスク質問ケース
- `cases.csv`: 実行時に使うケースセット
- `case_set_summary.json`: ケースセットの要約
- `reports/before_stale_v1/`: before gate artifact
- `reports/after_v2_reference/`: after gate artifact
- `before_after_onepager.md`: 顧客に見せる1枚比較
- `customer_gate_report.md`: 顧客提出用の短い判定レポート
- `customer_data_handling.md`: データ取扱い説明1枚
- `sales_demo_script.md`: 2分営業デモ台本
- `demo_summary.json`: before / after の機械可読サマリ

## Runtime severity note

`case_set_summary.json` reports both PoC selection bands and runtime severities. `S3` is used only to explain PoC case selection and classification. It is not a new runtime severity. Generated `cases.csv` rows keep the existing formal schema by writing S3-selected cases as `severity=S2` and preserving the original band in `notes` as `poc_band:S3`.

## 顧客向けメッセージ

Proof Gate は、RAG AIを置き換えるものではありません。FAQ・規約・料金表・プロンプト変更後に、古い条件や危険な回答が本番に出ないかを確認する品質ゲートです。

PoCで作る簡易RAGは、再現・診断・説明のための軽量構成です。そのまま本番RAGとして販売するものではありません。本格RAG構築では、顧客環境、セキュリティ、監視、改善サイクルを含めて設計します。
