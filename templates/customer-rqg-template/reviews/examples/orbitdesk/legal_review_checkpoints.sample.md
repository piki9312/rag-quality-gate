# Legal Review Checkpoints: OrbitDesk FAQ RAG

## Purpose

このサンプルは、OrbitDesk FAQ RAG案件で法務・契約担当に確認してもらう論点を整理する記入例です。

条項案や法的有効性の判断は行いません。ここでは、法務・契約担当に確認すべき可能性がある論点をレビュー証跡として整理します。

## Metadata

| Item | Value |
|---|---|
| review_id | ORBIT-LEGAL-2026-06-001 |
| customer / project | OrbitDesk株式会社 / OrbitDesk FAQ RAG導入支援 |
| vendor owner | Example AI Vendor PM |
| legal / contract reviewer | Customer / vendor legal reviewer |
| related_scope_sheet | `ai_scope_sheet.sample.md` |
| related_data_boundary_check | `data_ip_boundary_check.sample.md` |
| updated_at | 2026-06-16 |

## Checkpoints

| Area | Review question | Status | Owner | Notes |
|---|---|---|---|---|
| 契約形態 | 準委任想定で進める前提に問題がないか確認が必要か | 未確認 | Customer / Vendor Legal | 本サンプルでは契約形態の判断はしない |
| 成果物定義 | Gate report、ReviewPacket、review artifact、active cases.csvの扱いを整理する必要があるか | 確認中 | Vendor PM | 正式成果物と作業用artifactの区別を確認 |
| 顧客提供データ | FAQ、料金表、返金ポリシー、解約ポリシーの取り扱い範囲 | 確認中 | Customer Legal | raw dataはcustomer/vendor-controlled環境で扱う |
| ログ保存 | 問い合わせログ・生成回答ログの保存期間とアクセス範囲 | 未合意 | Customer Legal | 個人情報を含む可能性がある |
| 学習利用 | 問い合わせログや生成回答ログを改善に使うか | 未合意 | Customer / Vendor Legal | 学習利用は別途確認が必要な可能性 |
| 評価ケース再利用 | OrbitDesk固有評価ケースを他案件で使えるか | 未合意 | Customer / Vendor Legal | 顧客固有expected_answerを含む可能性 |
| 評価テンプレート再利用 | 抽象Case Intent、Failure Pattern、review templateの扱い | 確認中 | Vendor Legal | 顧客raw dataを含めない範囲で整理 |
| ベンダー既存資産 | Example AI Vendorの既存テンプレートや分類体系の扱い | 確認中 | Vendor Legal | 顧客固有カスタマイズと分ける |
| 顧客固有カスタマイズ | OrbitDesk向けprompt、回答方針、case review内容 | 未合意 | Customer / Vendor Legal | project-specific artifactとして確認 |
| 競業避止・横展開制限 | 同業他社案件への抽象知見の利用範囲 | 未合意 | Customer / Vendor Legal | 制限の有無を確認 |
| 損害賠償・責任範囲 | AI回答誤り、旧情報参照、過剰断定が発生した場合の扱い | 未確認 | Customer / Vendor Legal | 本テンプレートでは責任範囲を判断しない |

## Review Notes by Area

### Contract Form

- OrbitDesk案件では準委任想定として進行している。
- ただし、契約形態の評価や適否はこの資料では扱わない。
- 成果物、作業範囲、レビュー証跡の扱いを契約担当が確認する。

### Deliverables

- 顧客説明に使う想定のartifact:
  - Gate Review
  - customer-facing safe report
  - Release Risk Review
- 作業・レビュー用artifact:
  - `review_cases.yaml`
  - `pattern-draft-review.csv`
  - full evidence logs
- active `cases.csv` はGate実行対象として扱う。

### Customer Data

- OrbitDesk FAQ本文、問い合わせログ、契約条件、料金表本文は顧客提供データとして扱う。
- full source document textはProof Gate artifactに貼らない。
- safe summaryとartifact referenceでレビューする。

### Logs

- 問い合わせログの保存期間は未合意。
- 生成回答ログの保存範囲は未合意。
- 個人情報を含む問い合わせは自動回答対象外としてScope Sheetに記録済み。

### Training / Improvement Use

- 生成回答ログや問い合わせログの学習利用は未合意。
- 抽象化されたFailure PatternやCase Intentとして扱えるかは、顧客raw dataを除いた形で確認する。

### Evaluation Cases and Templates

- OrbitDesk固有のexpected_answerを含む評価ケースはcustomer/vendor-controlled artifactとして扱う。
- 抽象Case Intent、test design type、risk categoryは汎用資産候補。
- 再利用範囲は顧客・ベンダー間で確認する。

## Follow-Up Items

| Item | Owner | Due | Status |
|---|---|---|---|
| 問い合わせログの保存条件を確認 | Customer Legal | 2026-06-24 | open |
| 生成回答ログの改善利用を確認 | Customer / Vendor Legal | 2026-06-24 | open |
| OrbitDesk固有評価ケースの再利用範囲を確認 | Customer / Vendor Legal | 2026-06-25 | open |
| 顧客向け公開時の残留リスク説明を確認 | Customer Owner / Vendor PM | 2026-06-25 | open |

## Notes

- 本サンプルは条項案ではありません。
- 法的有効性の判断は行いません。
- 顧客raw data、契約文全文、問い合わせログ全文は含めていません。
