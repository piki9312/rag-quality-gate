# Release Risk Review: OrbitDesk FAQ RAG

## Purpose

このサンプルは、OrbitDesk FAQ RAG chatbot の本番反映前レビューにおいて、Gate結果とreview artifactをもとにリスクと次の対応を整理する記入例です。

Proof Gateが本番反映を最終決定するものではありません。今回の検証範囲では、修正後再検査、または人間確認付きの制限利用が判断候補になります。

## Metadata

| Item | Value |
|---|---|
| review_id | ORBIT-RELEASE-2026-06-001 |
| review_stage | release_gate |
| gate_run_id | orbit_release_review_2026_06_001 |
| gate_report_ref | `artifacts/orbitdesk/2026-06-pre-release/gate-report.json` |
| review_packet_ref | `artifacts/orbitdesk/2026-06-pre-release/review-packet.json` |
| review_artifact_ref | `reviews/orbitdesk/review_cases.yaml` |
| customer / project | OrbitDesk株式会社 / OrbitDesk FAQ RAG導入支援 |
| vendor owner | Example AI Vendor PM |
| customer owner | OrbitDesk Customer Support Lead |
| updated_at | 2026-06-16 |

## Review Scope

| Item | Description |
|---|---|
| Target AI / RAG system | FAQ RAG chatbot |
| Target document corpus | FAQ、料金表、返金ポリシー、解約ポリシー、操作手順書 |
| Target categories | 返金、解約、料金、契約条件、操作手順 |
| Evaluation cases | 重要質問20問 |
| Current phase | 本番反映前レビュー |

## Out of Scope

| Area | Reason |
|---|---|
| 法的判断 | 法務/契約担当確認が必要な可能性があるため |
| 個別契約交渉 | 顧客別条件に依存するため |
| 個人情報を含む問い合わせの自動回答 | 取り扱い条件が未合意のため |
| source document text全文レビュー | full evidenceはvendor/customer-controlled環境で扱うため |

## Input Artifacts

| Artifact | Reference | Notes |
|---|---|---|
| Gate report | `artifacts/orbitdesk/2026-06-pre-release/gate-report.json` | machine-readable result |
| Gate decision | `artifacts/orbitdesk/2026-06-pre-release/gate-decision.json` | decision support artifact |
| ReviewPacket | `artifacts/orbitdesk/2026-06-pre-release/review-packet.json` | dashboard/source review artifact |
| Active cases | `packs/orbitdesk/cases.csv` | Gate execution target |
| Review candidate artifact | `reviews/orbitdesk/review_cases.yaml` | vendor review material |

## Change Summary

| Change | Safe summary |
|---|---|
| Pricing documents | 現行料金表への更新が行われた |
| Refund policy | 返金対象外条件の明確化が行われた |
| Cancellation policy | 解約期限の表現が更新された |
| FAQ | 一部FAQの表現が統合された |

## Evaluation Case Summary

| Metric | Count |
|---|---:|
| Total cases | 20 |
| Pass | 14 |
| Warn | 3 |
| Block | 3 |
| S1重大リスク | 1 |
| S2リスク | 3 |
| 旧情報参照 | 1 |
| 根拠不一致 | 1 |
| 過剰断定 | 2 |

## Case List

| Case ID | Category | Result | Risk summary |
|---|---|---|---|
| OD-PRICE-004 | pricing | Block | 旧料金プランを案内した |
| OD-REFUND-002 | refund | Block | 返金対象外ケースで返金可能と案内した |
| OD-REFUND-006 | refund | Warn | 例外対応を根拠なく確約する表現があった |
| OD-CONTRACT-003 | contract_terms | Warn | 個別条件に関する断定があった |
| OD-CANCEL-005 | cancellation | Warn | 解約期限の補足確認が必要 |

## Major Risks

| Priority | Risk | Why it matters | Recommended next action |
|---|---|---|---|
| High | 旧料金プランを案内した | 顧客対応・請求案内に影響する可能性がある | 現行料金表への参照を修正し、pricingケースを再検査 |
| High | 返金対象外ケースで返金可能と案内した | 返金条件の根拠不一致がある | 返金ポリシーとの整合を修正し、refundケースを再検査 |
| Medium | 例外対応を根拠なく確約した | 文書にない対応を期待させる可能性がある | 断定表現を避け、人間確認へ回す方針に修正 |

## Unresolved Risks

| Risk | Owner | Status | Exit condition |
|---|---|---|---|
| pricingの旧情報参照 | Vendor Engineer | open | 修正後、OD-PRICE-004がpassまたはreview可能状態 |
| refundの根拠不一致 | Vendor QA | open | 修正後、OD-REFUND-002がpassまたはreview可能状態 |
| 例外対応の過剰断定 | Vendor QA | open | プロンプト/回答方針修正後、該当ケースを再検査 |
| 問い合わせログ保存条件 | Customer Legal / Vendor PM | 未合意 | Data/IP Boundary Checkで扱いを確認 |

## Customer Confirmation Items

| Item | Owner | Status |
|---|---|---|
| 人間確認付き制限利用を許容するか | Customer Owner | pending |
| 顧客向け公開前に再検査を必須にするか | Customer Owner / Vendor PM | pending |
| 問い合わせログ・生成回答ログの保存条件 | Customer Legal | pending |
| 顧客向け説明で残留リスクをどう表現するか | Customer Owner / Vendor PM | pending |

## Vendor Action Items

| Action | Owner | Due | Status |
|---|---|---|---|
| 料金参照のretriever / source priorityを確認 | Vendor Engineer | 2026-06-20 | open |
| 返金条件の回答方針を修正 | Vendor QA | 2026-06-20 | open |
| 例外対応を断定しないプロンプトに修正 | Vendor Engineer | 2026-06-21 | open |
| 同じreview_stageで再検査 | Vendor QA | 2026-06-22 | pending |

## Data / IP Open Items

| Item | Status | Reference |
|---|---|---|
| 問い合わせログ保存 | 未合意 | `data_ip_boundary_check.sample.md` |
| 生成回答ログの学習利用 | 未合意 | `data_ip_boundary_check.sample.md` |
| OrbitDesk固有評価ケースの再利用範囲 | 未合意 | `data_ip_boundary_check.sample.md` |

## Production Reflection Candidate

| Candidate | Current note |
|---|---|
| 修正後再検査 | 今回の検証範囲では最も自然な判断候補 |
| 人間確認付きの制限利用 | 顧客・ベンダーが未解決リスクと確認条件を受け入れる場合の候補 |
| そのまま本番反映 | 今回の検証範囲では推奨される候補ではない |

## Risk Acceptance Memo

| Item | Memo |
|---|---|
| Accepted by | 未記入 |
| Accepted scope | 未記入 |
| Conditions | 未記入 |
| Review date | 未記入 |

## Notes

- このサンプルはProof Gateが本番反映を最終決定する形式ではありません。
- source document text全文、raw logs、full evidenceは含めていません。
- 詳細はartifact referenceで確認する前提です。
