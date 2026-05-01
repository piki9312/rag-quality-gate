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
- ローカルfallback環境では gate report は `要確認` / `policy_status: NEEDS_HUMAN_REVIEW` になります。
- これは回答品質の失敗ではなく、検索モデルfallbackを検知した運用品質上の確認です。

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

## before reportで見る場所

- `1. 本番反映判定`: `NG` と `policy_status: BLOCK`
- `4. 実行結果サマリ`: `overall_pass_rate` と `s1_pass_rate`
- `5. S1重大失敗一覧`: どの高リスク質問で止まったか
- `8. 月額Monitorで継続確認すべき項目`: PoC後の継続監視理由

## after reportで見る場所

- `1. 本番反映判定`: `要確認` と `policy_status: NEEDS_HUMAN_REVIEW`
- `4. 実行結果サマリ`: `overall_pass_rate` と `s1_pass_rate`
- `5. S1重大失敗一覧`: 重大失敗がなくなっていること

## 顧客向けメッセージ

Proof Gate は、RAG AIを置き換えるものではありません。FAQ・規約・料金表・プロンプト変更後に、古い条件や危険な回答が本番に出ないかを確認する品質ゲートです。
