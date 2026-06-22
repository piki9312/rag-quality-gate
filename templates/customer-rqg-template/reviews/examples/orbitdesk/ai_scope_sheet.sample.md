# AI Scope Sheet: OrbitDesk FAQ RAG

## Purpose

このシートは、OrbitDesk FAQ RAG chatbot の利用範囲と、人間確認に残す領域を顧客・ベンダー間で確認するための記入例です。

Proof Gateは本番反映の最終判断を自動化しません。このサンプルは、顧客レビュー会で使う判断材料とレビュー証跡の例です。

## Metadata

| Item | Value |
|---|---|
| review_id | ORBIT-SCOPE-2026-06-001 |
| customer / project | OrbitDesk株式会社 / OrbitDesk FAQ RAG導入支援 |
| vendor owner | Example AI Vendor PM |
| customer owner | OrbitDesk Customer Support Lead |
| review_stage | release_gate |
| related_gate_run_id | orbitdesk-pre-release-2026-06-001 |
| related_report | `artifacts/orbitdesk/2026-06-pre-release/gate-report.json` |
| updated_at | 2026-06-16 |

## Project Overview

| Item | Description |
|---|---|
| Contract assumption | 準委任想定。ただし契約形態の判断は本シートでは行わない |
| Target AI | FAQ RAG chatbot |
| Purpose | 顧客問い合わせに対する一次回答支援 |
| Expected users | カスタマーサポート担当者。将来的には一部顧客向け利用を検討 |
| Current phase | 本番反映前レビュー |
| Target categories | 返金、解約、料金、契約条件、操作手順 |
| Source documents | FAQ、料金表、返金ポリシー、解約ポリシー、操作手順書 |

## In Scope

| Scope item | Notes | Owner |
|---|---|---|
| 返金条件の一次回答 | 文書ID `OD-REFUND-POLICY-2026-05` を参照。個別判断は人間確認へ回す | Vendor PM / Customer Support Lead |
| 解約手順の一次回答 | 解約申請フローと期限案内を対象にする | Vendor PM |
| 料金プランの案内 | 現行料金表のプラン名・対象範囲の案内に限定 | Customer Support Lead |
| 操作手順の案内 | 管理画面の一般的な操作手順を対象にする | Vendor QA |

## Out of Scope

| Out-of-scope item | Reason | User-facing handling |
|---|---|---|
| 個別契約交渉 | 顧客ごとの契約条件に依存するため | 担当営業または契約窓口へ案内 |
| 法的判断 | 担当者確認が必要な可能性があるため | 法務/契約担当の確認へ回す |
| 返金可否の最終判断 | 例外条件や契約条件の確認が必要な場合があるため | サポート責任者へエスカレーション |
| 例外対応の確約 | 文書にない例外をAIが確約しないため | 担当者確認が必要と案内 |
| 個人情報を含む問い合わせへの自動回答 | 取り扱い条件が未合意のため | 人間対応へ切り替え |

## Conditions for Production Use

| Condition | Required evidence or review | Status | Owner |
|---|---|---|---|
| 重要質問20問の検査結果を確認 | `gate-report.json` / ReviewPacket | in_progress | Vendor QA |
| S1/S2の未解決リスクを確認 | `release_risk_review.sample.md` | in_progress | Vendor PM |
| 旧料金参照を修正 | case `OD-PRICE-004` | open | Vendor Engineer |
| 返金条件の根拠不一致を修正 | case `OD-REFUND-002` | open | Vendor Engineer / QA |
| 過剰断定の回答方針を修正 | cases `OD-REFUND-006`, `OD-CONTRACT-003` | open | Vendor QA |
| 人間確認付き制限利用の条件を確認 | Scope sheet / behavior spec | pending | Customer Support Lead |

## Human Review Conditions

| Trigger | Required action | Owner | Notes |
|---|---|---|---|
| 返金可否が契約条件や例外条件に依存する | サポート責任者へ確認 | Customer Support Lead | AIは一次案内に留める |
| 料金表とFAQで表現が異なる | 文書オーナーへ確認 | Customer Docs Owner | 旧料金参照の疑いがある |
| 解約期限がプランや契約開始日に依存する | 契約担当へ確認 | Customer Contract Owner | 断定回答を避ける |
| 個人情報を含む問い合わせ | 人間対応に切り替え | Customer Support Lead | ログ保存条件も確認 |

## Customer Confirmation Items

| Confirmation item | Customer owner | Status | Notes |
|---|---|---|---|
| 対象カテゴリが本番反映前レビューの範囲として妥当か | Customer Support Lead | in_progress | 返金・解約・料金を重点確認 |
| 顧客向け利用を開始する前に制限利用期間を設けるか | Customer Owner | pending | 人間確認付き利用案あり |
| 個人情報を含む問い合わせの扱い | Security / Legal reviewer | pending | 自動回答対象外として整理 |
| 問い合わせログの保存・学習利用 | Legal / Contract reviewer | pending | Data/IP Boundary Checkに記録 |

## Vendor Action Items

| Action | Owner | Due | Status |
|---|---|---|---|
| 旧料金参照ケースを修正し再検査 | Vendor Engineer | 2026-06-20 | open |
| 返金条件の根拠不一致ケースを修正し再検査 | Vendor QA | 2026-06-20 | open |
| 過剰断定のプロンプト/回答方針を修正 | Vendor Engineer | 2026-06-21 | open |
| 制限利用案をRelease Risk Reviewに反映 | Vendor PM | 2026-06-21 | in_progress |

## Unresolved Items

| Item | Owner | Due | Status |
|---|---|---|---|
| 問い合わせログの保存期間 | Customer Legal / Vendor PM | 2026-06-24 | 未合意 |
| 生成回答ログの学習利用 | Customer Legal / Vendor PM | 2026-06-24 | 未合意 |
| 顧客向け公開時の表示文言 | Customer Owner / Vendor PM | 2026-06-25 | 未合意 |

## Notes

- 本サンプルは架空案件です。
- source document text全文、契約文全文、raw logs、full evidenceは含めていません。
- 詳細はartifact referenceで管理します。
