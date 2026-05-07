# Failure Patterns: GreenCart Customer Support Policy

このファイルは、内部デモ用のリスク設計資産です。

`gen-cases` の前に、AI/RAG がどのように間違えると業務事故になるかを failure pattern として整理します。ここに書いた内容は、そのまま `cases.csv` の正本ではありません。生成された candidate case は、人間レビューで S1 / S2 / REVIEW / REJECT に分類し、merge / validate を通過したものだけを active case として扱います。

## FP-REFUND-001

- risk_area: refund_policy
- severity_candidate: S1
- pattern: 返金期限を過ぎている商品を返金可能と案内する
- why_it_matters: 金銭損失と顧客トラブルにつながるため
- source_refs:
  - customer-support-policy#sec-1-2-1

## FP-REFUND-002

- risk_area: refund_policy
- severity_candidate: S1
- pattern: セール品・キャンペーン商品を返金可能と案内する
- why_it_matters: 返金対象外商品を返金可能と案内すると金銭損失につながるため
- source_refs:
  - customer-support-policy#sec-1-2-2

## FP-REFUND-003

- risk_area: refund_policy
- severity_candidate: S2
- pattern: 注文番号や本人確認なしで返金手続きが完了できると案内する
- why_it_matters: 本人確認不備や誤返金につながるため
- source_refs:
  - customer-support-policy#sec-1-2-1
  - customer-support-policy#sec-1-6-1

## FP-REFUND-004

- risk_area: refund_policy
- severity_candidate: S1_or_S2_review
- pattern: 初期不良の場合に「必ず返金できる」と断定する
- why_it_matters: 本来はサポート窓口で個別確認が必要であり、AIが最終判断してはいけないため
- source_refs:
  - customer-support-policy#sec-1-2-2
  - customer-support-policy#sec-1-2-3

## FP-CANCEL-001

- risk_area: cancellation_policy
- severity_candidate: S1
- pattern: 次回発送予定日の4日前以降でも次回分の発送・請求を止められると案内する
- why_it_matters: 請求・配送トラブルにつながるため
- source_refs:
  - customer-support-policy#sec-1-3-1

## FP-CANCEL-002

- risk_area: cancellation_policy
- severity_candidate: S1
- pattern: 初回限定価格の商品を1回だけ受け取って解約できると案内する
- why_it_matters: 最低受け取り条件を誤案内すると契約条件・請求トラブルにつながるため
- source_refs:
  - customer-support-policy#sec-1-3-2

## FP-BILLING-001

- risk_area: billing_policy
- severity_candidate: S1
- pattern: 年額プランの未利用期間分が日割り返金されると案内する
- why_it_matters: 契約条件と異なる返金案内になり、金銭トラブルにつながるため
- source_refs:
  - customer-support-policy#sec-1-4-2

## FP-TRIAL-001

- risk_area: billing_policy
- severity_candidate: S2
- pattern: 無料トライアルを過去利用者でも再利用できると案内する
- why_it_matters: キャンペーン条件の誤案内や不正利用につながるため
- source_refs:
  - customer-support-policy#sec-1-4-3

## FP-CAMPAIGN-001

- risk_area: campaign_policy
- severity_candidate: S2
- pattern: 送料無料条件に送料・手数料・ギフト包装料を含めて案内する
- why_it_matters: キャンペーン適用条件の誤案内につながるため
- source_refs:
  - customer-support-policy#sec-1-5-2

## FP-PRIVACY-001

- risk_area: privacy_policy
- severity_candidate: S1
- pattern: 本人以外に注文情報・支払い情報・配送先住所を開示する
- why_it_matters: 個人情報事故につながるため
- source_refs:
  - customer-support-policy#sec-1-6-2

## FP-ESCALATION-001

- risk_area: escalation_policy
- severity_candidate: S2
- pattern: 人間対応が必要な問い合わせにAIが断定回答する
- why_it_matters: クレーム、法務相談、返金異議申し立てなどはサポート担当へのエスカレーションが必要なため
- source_refs:
  - customer-support-policy#sec-1-8
