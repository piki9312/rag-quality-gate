# Proof Gate付きRAG AI導入診断PoC 提案メモ

## 目的

この1枚は、顧客向けFAQ RAG AIに対して、Proof Gate付きRAG AI導入診断PoCをどう提案するかを短く整理した資料です。

伝えたいことはシンプルです。

1. FAQ・規約・プロンプト変更は継続的に起きる。
2. RAG AIは自然に見えても、古い条件のまま答えることがある。
3. それが返金・解約・料金・契約条件で起きると、顧客向けの変更事故になる。
4. Proof Gateは、本番反映前に高リスク質問を確認し、危ない回答を止める。

## デモで使うファイル

- デモ一式: `demos/customer_support_faq_change/`
- before report: `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- after report: `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- 比較要約: `demos/customer_support_faq_change/demo_summary.json`

## 話す順番

### Before

- stale v1 report を開く。
- `1. 本番反映判定` を見せ、リリース判定が `NG` であることを伝える。
- `5. S1重大失敗一覧` に移り、7日以内返金の質問が旧ルールで答えられていることを示す。
- 変更後FAQではキャンペーン条件が厳しくなっているのに、AIが古い条件を案内していると説明する。

### After

- v2 reference report を開く。
- `1. 本番反映判定` が `OK` に変わっていることを示す。
- `5. S1重大失敗一覧` が解消していることを見せる。
- 同じ高リスク質問セットを更新後FAQで再判定し、危ない回答が通らなくなったことを説明する。

### クロージング

- `demo_summary.json` を開く。
- before / after の S1 pass rate、overall pass rate、S1 failures を比較する。
- 最後に、Proof GateはRAGを置き換えるものではなく、変更後の回答を本番に出してよいかを確認する仕組みだと伝える。

## 月額Monitorが必要な理由

- 一度通ったAIでも、FAQ・規約・プロンプト変更のあとに再び危ない回答へ戻ることがある。
- 返金・解約・料金・契約条件は、継続監視しないと事故が見えにくい。
- 月額Monitorで高リスク質問を定期実行することで、変更事故の再発を早く見つけやすくなる。

## 顧客向けの一言

Proof Gateを入れることで、FAQ変更後の危ない旧回答を本番前に止め、修正後に同じ高リスク質問で改善まで説明できます。