# Customer Support FAQ変更事故 Before / After 1枚メモ

## 目的

FAQ・規約・料金表の変更後に、RAG AI が古い条件で答えてしまうリスクを、Proof Gate が本番前に検知できることを示します。

## Before / After Summary

| 項目 | Before: stale v1 | After: v2 reference |
|---|---:|---:|
| 本番反映判定 | NG | 要確認 |
| policy_status | BLOCK | NEEDS_HUMAN_REVIEW |
| S1 pass rate | `demo_summary.json` を参照 | `demo_summary.json` を参照 |
| overall pass rate | `demo_summary.json` を参照 | `demo_summary.json` を参照 |
| S1 failures | `demo_summary.json` を参照 | `demo_summary.json` を参照 |
| 顧客向けメッセージ | 古いFAQ条件で回答しており、本番反映前に止める必要がある | S1重大失敗は解消。fallback検知により運用確認は必要 |

## 代表的なS1重大失敗

`demo_summary.json` の `representative_s1_failure` を参照します。

見るポイント:

- `case_id`
- `question`
- `ai_answer`
- `fail_reason`
- `risk_domain`

## 顧客向け説明

Before:

AIの回答文は自然でも、現在のFAQ条件と違う回答をしている場合があります。返金・解約・料金・契約条件の誤案内は顧客影響が大きいため、本番反映前に止める必要があります。

After:

FAQ更新後に、同じ高リスク質問セットで再Gateします。S1重大失敗が解消していれば、修正が有効だったことを説明できます。このローカル実行では検索モデルfallbackにより要確認扱いですが、回答品質の重大失敗は解消しています。

## 月額Monitorにつながる理由

- FAQ・規約・料金表は継続的に変わる
- プロンプトや検索設定の変更でも回答品質は劣化する
- 一度通ったAIでも、変更後に危険な回答へ戻ることがある
- 高リスク質問を定期実行することで、変更事故を見逃しにくくなる

## 開くファイル

- `reports/before_stale_v1/gate-report.md`
- `reports/after_v2_reference/gate-report.md`
- `demo_summary.json`
- `sales_demo_script.md`
