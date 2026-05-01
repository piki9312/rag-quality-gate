# カスタマーサポートFAQ変更事故 Before / After 1枚メモ

## この1枚の使い方

営業や顧客説明の場で、Proof Gate付きRAG AI導入診断PoCの結果を1画面で示したいときに使います。

## Before / After 比較

| 項目 | Before: stale v1（旧FAQ参照のまま） | After: v2 reference（更新後FAQで再判定） |
|---|---:|---:|
| 本番反映判定 | NG | OK |
| policy_status | BLOCK | PASS |
| S1 pass rate | 0.0% | 100.0% |
| overall pass rate | 33.3% | 100.0% |
| S1 failures | 3 | 0 |
| 代表S1重大失敗 | customer_support_faq_001: 7日以内返金を旧ルールで許容 | 解消 |
| 顧客向け一言コメント | 古いFAQ条件のまま自然に答えてしまうため、本番前に止める必要がある | 更新後の回答は新ルールに沿っており、同じ高リスク質問でも通過した |

## 代表S1重大失敗

- Case ID: `customer_support_faq_001`
- 質問: `購入から7日以内なら返金できますか？`
- fail_reason: `Keyword match 33% < 80%`
- 顧客影響の意味: AIが古いv1返金ルールで答えており、通常商品まで通常の7日返金対象のように案内してしまっている。

## 顧客向け説明

Before:

回答文は自然に見えても、実際には古い返金条件を案内しているため、そのまま本番に出すと顧客向けの説明事故につながります。

After:

FAQ更新後に同じ高リスク質問で再判定すると、S1重大失敗が解消し、本番反映判定も安全に説明できる状態になります。

## デモ中に開くファイル

- `reports/before_stale_v1/gate-report.md`
- `reports/after_v2_reference/gate-report.md`
- `demo_summary.json`
- `sales_demo_script.md`