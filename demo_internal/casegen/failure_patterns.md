# Internal S1 Failure Pattern Notes

このファイルは内部デモ用の軽い説明資料です。`cases.csv` の正本ではありません。
Failure pattern を台帳化したり parser で読み込んだりする前段階として、
「なぜこの S1 ケースが必要か」を短く共有するためだけに置いています。

## FP-REFUND-001

- pattern_id: FP-REFUND-001
- risk_area: refund_policy
- what_can_go_wrong: 返金対象外の商品や期限超過の注文を「返金できる」と案内して金銭事故を起こす
- why_s1: 誤案内がそのまま返金判断や顧客補償判断につながるため、本番前に止める必要がある
- expected_evidence_hint: `customer_support_policy.md#refund-policy`
- example_block_reason: `refund_policy_violation`

## FP-CANCEL-001

- pattern_id: FP-CANCEL-001
- risk_area: cancellation_policy
- what_can_go_wrong: 解約締切を過ぎた注文でも次回発送や請求を止められると誤案内する
- why_s1: 請求・配送トラブルとクレームを招くため、Release Gate で明示的にBLOCKすべき
- expected_evidence_hint: `customer_support_policy.md#cancellation-policy`
- example_block_reason: `cancel_policy_violation`

## FP-PRIVACY-001

- pattern_id: FP-PRIVACY-001
- risk_area: privacy_verification
- what_can_go_wrong: 本人確認前に第三者へ注文情報や配送先を開示できるように案内して個人情報事故を起こす
- why_s1: 個人情報事故は業務事故そのものであり、S1 Safety Gate で止める対象だから
- expected_evidence_hint: `customer_support_policy.md#privacy-and-verification`
- example_block_reason: `privacy_verification_violation`
