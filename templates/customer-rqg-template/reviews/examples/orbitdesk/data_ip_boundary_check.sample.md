# Data / IP Boundary Check: OrbitDesk FAQ RAG

## Purpose

このサンプルは、OrbitDesk FAQ RAG案件における顧客提供データ、評価ケース、テンプレート、改善ノウハウの境界を整理する記入例です。

この文書は知財帰属や契約条件を確定するものではありません。未合意論点は顧客・ベンダー間、必要に応じて法務/契約担当で確認します。

## Metadata

| Item | Value |
|---|---|
| review_id | ORBIT-DATA-IP-2026-06-001 |
| customer / project | OrbitDesk株式会社 / OrbitDesk FAQ RAG導入支援 |
| vendor owner | Example AI Vendor PM |
| customer owner | OrbitDesk Customer Support Lead |
| related_scope_sheet | `ai_scope_sheet.sample.md` |
| related_contract_or_order | `contract-ref: ORBIT-ORDER-2026-Q2` |
| updated_at | 2026-06-16 |

## Data / Artifact Boundary

| Item | Example in this project | Current handling | Reuse / learning note | Status |
|---|---|---|---|---|
| 顧客提供データ | OrbitDesk FAQ本文 | Customer-controlled artifact | 横展開利用は確認が必要 | 確認中 |
| RAG文書 | FAQ、料金表、返金ポリシー、解約ポリシー、操作手順書 | Vendor/customer-controlled environment | source document text全文はProof Gate artifactに貼らない | 合意済み方針 |
| 問い合わせログ | サポート問い合わせログ | 今回のreview artifactには含めない | 保存・学習利用は未合意 | 未合意 |
| 生成回答ログ | Gate実行時の回答ログ | full evidenceとしてvendor環境に保持 | safe summaryのみ共有候補 | 確認中 |
| プロンプト | OrbitDesk向けRAG prompt | Vendor/customer-controlled artifact | 汎用prompt方針と顧客固有調整の分離が必要 | 確認中 |
| 評価ケース | OrbitDesk固有 `cases.csv` | Vendor/customer-controlled artifact | 顧客固有expected_answerを含む可能性がある | 確認中 |
| 評価テンプレート | Case Intent / test design template | Vendor / Proof Gate abstract asset candidate | 顧客固有情報を含まない形で再利用候補 | 確認中 |
| リスク分類体系 | stale_reference, evidence_mismatchなど | Abstract classification | 顧客横断で再利用候補 | 確認中 |
| レポートテンプレート | Gate Review / release risk review | Template asset | 顧客raw dataを除いたテンプレートとして再利用候補 | 確認中 |
| 改善ノウハウ | 旧料金参照を防ぐ運用知見 | Safe summaryとして抽象化 | 顧客固有文書を含めない形で整理 | 確認中 |
| 顧客固有カスタマイズ | OrbitDesk向け回答方針 | Customer/vendor-controlled artifact | 再利用範囲は確認が必要 | 未合意 |
| ベンダー汎用資産 | 評価観点、レビュー形式 | Vendor asset candidate | 契約・合意範囲に従う | 確認中 |

## Review Questions

| Question | Current answer candidate | Owner | Status |
|---|---|---|---|
| OrbitDesk FAQ本文をProof Gate運営側に送る前提か | 送らない。vendor/customer-controlled環境で扱う | Vendor PM | 確認済み |
| full source document textをreview artifactに貼るか | 貼らない。document id / artifact referenceで扱う | Vendor QA | 確認済み |
| 問い合わせログの保存期間は決まっているか | 未合意 | Customer Legal / Vendor PM | 未合意 |
| 生成回答ログを学習利用するか | 未合意 | Customer Legal / Vendor PM | 未合意 |
| OrbitDesk固有評価ケースを他案件で再利用できるか | 確認が必要 | Customer Owner / Vendor PM | 未合意 |
| 抽象化したFailure Patternを改善資産として扱うか | 顧客raw dataを含めない範囲で候補 | Vendor PM | 確認中 |

## Learning / Reuse Boundary

| Asset | Reuse candidate | Required confirmation |
|---|---|---|
| Case Intent | yes, if abstract | 顧客固有文言を含めないこと |
| Failure Pattern | yes, if abstract | 顧客名・FAQ本文・ログを含めないこと |
| Question Variation | yes, if customer-neutral | 顧客固有条件を含めないこと |
| OrbitDesk expected_answer | no by default | 顧客・ベンダー間で確認が必要 |
| OrbitDesk source documents | no by default | 顧客管理範囲として扱う |
| Safe summary trend | possible | 顧客raw dataを含めないこと |

## Legal / Contract Review Candidates

| Item | Why review may be needed | Current status |
|---|---|---|
| 問い合わせログの保存 | 個人情報や顧客データ取り扱いに関係する可能性 | 未合意 |
| 生成回答ログの学習利用 | 顧客データ利用範囲に関係する可能性 | 未合意 |
| 評価ケースの再利用 | 顧客固有要素を含む可能性 | 未合意 |
| 顧客固有promptの扱い | project-specific customizationの扱い確認が必要 | 確認中 |
| テンプレート/分類体系の再利用 | 抽象資産と顧客固有資産の分離が必要 | 確認中 |

## Notes

- 本サンプルは架空案件です。
- 契約文、FAQ本文、問い合わせログ、full evidenceは含めていません。
- 未合意項目は「確認が必要」として残しています。
