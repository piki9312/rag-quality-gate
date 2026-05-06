# Customer Support FAQ変更事故デモ

このディレクトリは、Proof Gate付き RAG AI導入診断PoCを短時間で見せるための before / after 営業デモです。

## 最短手順

```powershell
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

生成後、次の順で開きます。

1. `sales_demo_script.md`
2. `reports/before_stale_v1/gate-report.md`
3. `reports/after_v2_reference/gate-report.md`
4. `before_after_onepager.md`
5. `demo_summary.json`

## デモで見せること

Before:

- FAQ v1 のままでは、返金・解約・料金・契約条件の回答が古い条件になります。
- Proof Gate は S1重大失敗として検知します。
- gate report は `NG` / `policy_status: BLOCK` になります。

After:

- FAQ v2 に更新した後、同じ高リスク質問セットで再Gateします。
- S1重大失敗が解消します。
- このコミット済みデモ artifact では gate report は `OK` / `policy_status: PASS` です。
- つまり、対象文書範囲では重大誤回答を解消した状態まで改善できたことを説明できます。
- 変更事故は今後も起こり得るため、PoC後は Monitor で継続確認する理由につなげます。

> evaluator fallback による `NEEDS_HUMAN_REVIEW` の説明が必要な場合は、`packs/customer_support_pack/reports/demo_runs/csp-needs-review-fallback-202604/` の固定artifactを別シナリオとして使います。

## 顧客向け資料と内部資料の役割

- `before_after_onepager.md`: 顧客向けの1枚要約
- `sales_demo_script.md`: 商談で話す順番の台本
- `reports/.../gate-report.md`: 実行結果の詳細
- `demo_summary.json`: 機械可読の要約

## ディレクトリ構成

- `demo_faq_v1.md`: before用の古いFAQ
- `demo_faq_v2.md`: after用の更新済みFAQ
- `generated_cases.csv`: デモ用に選んだ高リスク質問ケース
- `cases.csv`: 実行時に使うケースセット
- `case_set_summary.json`: ケースセットの要約
- `reports/before_stale_v1/`: before gate artifact
- `reports/after_v2_reference/`: after gate artifact
- `before_after_onepager.md`: 顧客に見せる1枚比較
- `sales_demo_script.md`: 2分営業デモ台本
- `demo_summary.json`: before / after の機械可読サマリ

## Runtime severity note

`case_set_summary.json` reports both PoC selection bands and runtime severities. `S3` is used only to explain PoC case selection and classification. It is not a new runtime severity. Generated `cases.csv` rows keep the existing formal schema by writing S3-selected cases as `severity=S2` and preserving the original band in `notes` as `poc_band:S3`.

## before reportで見る場所

- `1. 本番反映判定`: `NG` と `policy_status: BLOCK`
- `4. 実行結果サマリ`: `overall_pass_rate` と `s1_pass_rate`
- `5. S1重大失敗一覧`: どの高リスク質問で止まったか
- `8. 月額Monitorで継続確認すべき項目`: PoC後の継続監視理由

## after reportで見る場所

- `1. 本番反映判定`: `OK` と `policy_status: PASS`
- `4. 実行結果サマリ`: `overall_pass_rate` と `s1_pass_rate`
- `5. S1重大失敗一覧`: 重大失敗がなくなっていること
- `8. 月額Monitorで継続確認すべき項目`: 変更後も継続監視が必要な理由

## 顧客向けメッセージ

Proof Gate は、RAG AIを置き換えるものではありません。FAQ・規約・料金表・プロンプト変更後に、古い条件や危険な回答が本番に出ないかを検査し、リリース判断を支援する品質ゲートです。
