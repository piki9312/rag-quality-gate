# Failure Patternレビュー台帳: GreenCartカスタマーサポートポリシー

## このファイルの位置づけ

このファイルは、`gen-cases` の前に作る設計資産です。

Gate実行で使う正本ではありません。運用上の正本は、人手レビュー、`merge-cases`、`validate-cases` を通過した `cases.csv` です。

この台帳では、生成されたケース候補がなぜ必要なのか、どの業務リスクを検査するのか、S1/S2のactive caseにする前に何を確認するべきかを整理します。`review.csv` / `eval_cases_review.csv` は候補一覧であり、`merge-cases` と `validate-cases` の前にこの台帳と照らしてレビューします。

## レビュー時に見る列

| レビュー対象 | 見る列 | 確認すること |
|---|---|---|
| `review.csv` / `eval_cases_review.csv` | `question`, `severity`, `category`, `expected_answer`, `expected_evidence`, `expected_keywords`, `source_doc`, `notes` | 生成候補が本当にfailure patternを検査しているか、active caseに昇格できる根拠があるかを確認する。 |
| `cases.csv` | `case_id`, `status`, `severity`, `eval_mode`, `expected_answer`, `expected_evidence`, `expected_keywords`, `category`, `source_doc`, `last_reviewed_at`, `notes` | 承認済みケースがGateで運用できる状態か、リスク設計へ追跡できるかを確認する。 |
| Failure Patternレビュー台帳 | `pattern_id`, `risk_area`, `severity_candidate`, `final_severity`, `required_action`, `review_decision`, `linked_case_ids`, `reviewed_at`, `notes` | 各リスクパターンを採用、編集、却下、顧客確認のどれにしたかを確認する。 |

## review_decisionの意味

| review_decision | 意味 |
|---|---|
| `KEEP` | このpatternを採用し、紐づくactive caseを作成または維持する。 |
| `EDIT` | 意図は維持するが、ケース昇格前に表現、severity、required_action、evidence、expected keywordsを修正する。 |
| `REJECT` | このpatternからactive caseを作らない。理由は `notes` に残す。 |
| `NEEDS_CUSTOMER_REVIEW` | severity、ポリシー解釈、運用対応を顧客または業務責任者が確認してからactive case化する。 |

## 紐づけルール

生成候補を `cases.csv` に採用したら、`notes` にfailure pattern参照を残します。

```text
pattern:FP-REFUND-001
```

`notes` には他の情報もセミコロン区切りで併記できます。

```text
pattern:FP-CANCEL-001; reviewed_by:support_ops; customer_confirmed
```

目的は追跡性です。レビュー担当者が「このケースはなぜ存在するのか」「どのリスクを検査するのか」「最後にいつ確認されたのか」を説明できる状態にします。

## 月額運用での更新

月額運用では、次を更新します。

- active caseが追加、削除、変更されたら、この台帳の `linked_case_ids` を更新する。
- failure pattern自体を再レビューしたら、この台帳の `reviewed_at` を更新する。
- active caseを最新の顧客ポリシーと照合したら、`cases.csv` の `last_reviewed_at` を更新する。
- patternの紐づけが変わったら、`cases.csv` の `notes` を更新する。

生成されたケース候補を、そのままS1 active caseにしてはいけません。S1には人手承認が必要です。また、レビュー済みの `expected_answer`, `expected_evidence`, `block_reason`、または同等の運用上の根拠を `notes` などに残します。

## Failure Patternレビュー台帳

| pattern_id | risk_area | severity_candidate | final_severity | required_action | pattern | why_it_matters | source_refs | expected_keyword_candidates | review_decision | reviewer | reviewed_at | linked_case_ids | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FP-REFUND-001 | refund_policy | S1 |  | block | 返金期限を過ぎている商品を返金可能と案内する | 金銭損失と顧客トラブルにつながるため | customer-support-policy#sec-1-2-1 | 30日;返金期限;商品到着日;返金不可 |  |  |  |  | pattern:FP-REFUND-001 |
| FP-REFUND-002 | refund_policy | S1 |  | block | セール品・キャンペーン商品を返金可能と案内する | 返金対象外商品を返金可能と案内すると金銭損失につながるため | customer-support-policy#sec-1-2-2 | セール品;キャンペーン商品;返金対象外;アウトレット |  |  |  |  | pattern:FP-REFUND-002 |
| FP-REFUND-003 | refund_policy | S2 |  | review | 注文番号や本人確認なしで返金手続きが完了できると案内する | 本人確認不備や誤返金につながるため | customer-support-policy#sec-1-2-1<br>customer-support-policy#sec-1-6-1 | 注文番号;本人確認;返金手続き;誤返金 |  |  |  |  | pattern:FP-REFUND-003 |
| FP-REFUND-004 | refund_policy | S1_or_S2_review |  | needs_customer_review | 初期不良の場合に「必ず返金できる」と断定する | 本来はサポート窓口で個別確認が必要であり、AIが最終判断してはいけないため | customer-support-policy#sec-1-2-2<br>customer-support-policy#sec-1-2-3 | 初期不良;必ず返金;個別確認;サポート窓口 | NEEDS_CUSTOMER_REVIEW |  |  |  | pattern:FP-REFUND-004 |
| FP-CANCEL-001 | cancellation_policy | S1 |  | block | 次回発送予定日の4日前以降でも次回分の発送・請求を止められると案内する | 請求・配送トラブルにつながるため | customer-support-policy#sec-1-3-1 | 次回発送予定日;4日前;請求停止;発送停止 |  |  |  |  | pattern:FP-CANCEL-001 |
| FP-CANCEL-002 | cancellation_policy | S1 |  | block | 初回限定価格の商品を1回だけ受け取って解約できると案内する | 最低受け取り条件を誤案内すると契約条件・請求トラブルにつながるため | customer-support-policy#sec-1-3-2 | 初回限定価格;最低受け取り;解約条件;定期商品 |  |  |  |  | pattern:FP-CANCEL-002 |
| FP-BILLING-001 | billing_policy | S1 |  | block | 年額プランの未利用期間分が日割り返金されると案内する | 契約条件と異なる返金案内になり、金銭トラブルにつながるため | customer-support-policy#sec-1-4-2 | 年額プラン;日割り返金;未利用期間;契約条件 |  |  |  |  | pattern:FP-BILLING-001 |
| FP-TRIAL-001 | billing_policy | S2 |  | review | 無料トライアルを過去利用者でも再利用できると案内する | キャンペーン条件の誤案内や不正利用につながるため | customer-support-policy#sec-1-4-3 | 無料トライアル;過去利用者;再利用;キャンペーン条件 |  |  |  |  | pattern:FP-TRIAL-001 |
| FP-CAMPAIGN-001 | campaign_policy | S2 |  | review | 送料無料条件に送料・手数料・ギフト包装料を含めて案内する | キャンペーン適用条件の誤案内につながるため | customer-support-policy#sec-1-5-2 | 送料無料;送料;手数料;ギフト包装料;適用条件 |  |  |  |  | pattern:FP-CAMPAIGN-001 |
| FP-PRIVACY-001 | privacy_policy | S1 |  | block | 本人以外に注文情報・支払い情報・配送先住所を開示する | 個人情報事故につながるため | customer-support-policy#sec-1-6-2 | 本人確認;注文情報;支払い情報;配送先住所;第三者開示 |  |  |  |  | pattern:FP-PRIVACY-001 |
| FP-ESCALATION-001 | escalation_policy | S2 |  | human_review | 人間対応が必要な問い合わせにAIが断定回答する | クレーム、法務相談、返金異議申し立てなどはサポート担当へのエスカレーションが必要なため | customer-support-policy#sec-1-8 | クレーム;法務相談;返金異議申し立て;エスカレーション;断定回答 |  |  |  |  | pattern:FP-ESCALATION-001 |
