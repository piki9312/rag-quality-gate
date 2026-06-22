# AI Behavior Spec: OrbitDesk FAQ RAG

## Purpose

このサンプルは、OrbitDesk FAQ RAG chatbot の回答方針、回答禁止領域、不明時の挙動、重大リスクを整理する記入例です。

Proof Gateは顧客固有の正解を確定しません。生成された回答やexpected answerは、顧客・ベンダーの確認を経てactive caseとして扱います。

## Metadata

| Item | Value |
|---|---|
| review_id | ORBIT-BEHAVIOR-2026-06-001 |
| customer / project | OrbitDesk株式会社 / OrbitDesk FAQ RAG導入支援 |
| system name | OrbitDesk FAQ RAG chatbot |
| related_scope_sheet | `ai_scope_sheet.sample.md` |
| related_gate_run_id | orbit_release_review_2026_06_001 |
| updated_at | 2026-06-16 |

## Basic Answer Policy

| Policy | Detail |
|---|---|
| Source-grounded answer | 根拠文書に基づいて回答する |
| Unclear source | 根拠が不足する場合は「確認が必要」と回答する |
| High-risk answer | 返金可否、例外対応、契約条件は断定せず人間確認へ回す |
| Current document priority | 旧料金や旧ポリシーを案内しない |
| Scope boundary | 法的判断や個別契約交渉には回答しない |

## Answerable Categories

| Category | Answer condition | Required source type | Human owner |
|---|---|---|---|
| 返金 | 返金ポリシーに明記された一般条件のみ | refund_policy | Customer Support Lead |
| 解約 | 解約手順と申請期限の一般案内のみ | cancellation_policy | Customer Contract Owner |
| 料金 | 現行料金表に記載されたプラン説明のみ | pricing_table | Customer Docs Owner |
| 契約条件 | FAQに明記された範囲の一般案内のみ | contract_terms_summary | Customer Contract Owner |
| 操作手順 | 操作手順書にある手順のみ | product_manual | Customer Support Lead |

## Prohibited or Human-Review Categories

| Category | Reason | Required handling |
|---|---|---|
| 個別契約交渉 | 顧客別条件に依存するため | 契約担当へ案内 |
| 返金可否の最終判断 | 例外条件や過去対応が関係する可能性があるため | サポート責任者へ確認 |
| 法的判断 | 専門担当確認が必要な可能性があるため | 法務/契約担当へ確認 |
| 個人情報を含む問い合わせ | 取り扱い条件が未合意のため | 自動回答せず人間対応 |
| 例外対応の確約 | 文書根拠がない場合があるため | 確約せず確認へ回す |

## Source Document Handling

| Source type | Handling |
|---|---|
| FAQ | 現行FAQの文書IDを参照し、旧FAQとの混在を避ける |
| Pricing table | 現行料金表のみを参照する |
| Refund policy | 返金対象、対象外、確認条件を分けて扱う |
| Cancellation policy | 期限、手続き、確認先を分けて扱う |
| Product manual | 操作手順の範囲に限定する |

## Unknown / Insufficient Evidence Behavior

| Situation | Expected behavior | Escalation owner |
|---|---|---|
| 根拠文書が見つからない | 確認が必要と回答し、担当者確認へ回す | Vendor QA |
| 複数文書で内容が異なる | AIが一方を選ばず、文書オーナー確認へ回す | Customer Docs Owner |
| 例外対応を求められる | 例外対応を確約せず、サポート責任者へ回す | Customer Support Lead |
| 個別契約条件を聞かれる | 契約担当へ確認が必要と案内する | Customer Contract Owner |

## High-Risk Areas

| Domain | Risk reason | Linked severity | Required behavior |
|---|---|---|---|
| refund | 誤案内が返金対応や顧客信頼に影響する | S1 / S2 | 根拠がある一般条件のみ案内 |
| cancellation | 解約期限の誤案内が契約対応に影響する | S1 / S2 | 期限と例外を断定しない |
| pricing | 旧料金案内が商談・請求対応に影響する | S1 / S2 | 現行料金表に限定 |
| contract_terms | 個別条件と一般条件の混同リスクがある | S1 / S2 | 契約担当確認へ回す |

## Prohibited Answer Examples

| Example | Why it is not acceptable | Safer handling |
|---|---|---|
| 「このケースは必ず返金されます」 | 返金可否の最終判断を断定している | 一般条件を示し、確認先へ回す |
| 「旧Basicプランの料金で利用できます」 | 旧料金参照の可能性がある | 現行料金表の確認が必要とする |
| 「例外対応できます」 | 根拠にない例外対応を確約している | 個別確認が必要とする |
| 「解約期限はいつでも大丈夫です」 | 解約期限を誤案内する可能性がある | 解約ポリシーの期限を確認 |

## Major Risk Definitions

| Risk | Example | Linked review marker |
|---|---|---|
| 旧料金を案内する | 廃止済みプランを案内 | pattern:stale_reference |
| 返金対象外ケースで返金可能と案内する | 根拠文書と回答が一致しない | pattern:evidence_mismatch |
| 解約期限を誤案内する | 申請期限を短く/長く案内 | pattern:business_rule_violation |
| 根拠にない例外対応を確約する | 文書にない特別対応を断定 | pattern:major_misguidance |

## Link to Evaluation Cases

| Case ID | Category | Behavior under review | Current status |
|---|---|---|---|
| OD-PRICE-004 | pricing | 旧料金参照をしない | block |
| OD-REFUND-002 | refund | 返金条件を根拠文書と一致させる | block |
| OD-REFUND-006 | refund | 例外対応を過剰断定しない | warn |
| OD-CONTRACT-003 | contract_terms | 個別契約条件を一般回答しない | warn |

## Review Checklist

- [ ] 回答可能カテゴリが確認されている。
- [ ] 回答禁止カテゴリが確認されている。
- [ ] 不明時の挙動が確認されている。
- [ ] 高リスク領域がS1/S2 reviewに接続されている。
- [ ] 重大リスクケースは修正後に再検査する。

## Notes

- 本サンプルはsafe summaryのみを記載しています。
- source document text全文やfull evidenceはartifact referenceで管理します。
