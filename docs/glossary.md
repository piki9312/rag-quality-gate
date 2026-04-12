# 用語集 / Glossary

RQG ドキュメントで使用される略語・用語の定義。

## 略語

| 略語 | 正式名 | 説明 |
|------|--------|------|
| RQG | RAG Quality Gate | 本プロジェクトの略称 |
| S1 | Severity 1 | 重大ケース（法令違反リスク、期限・金額誤案内等）。100% 合格必須 |
| S2 | Severity 2 | 準重大ケース（手順不足、説明品質劣化等） |
| KPI | Key Performance Indicator | 品質指標（keyword_match_rate, retrieval_hit_rate 等） |
| SLO | Service Level Objective | ゲート判定に使う合格基準（s1_pass_rate, overall_pass_rate 等） |
| ROI | Return on Investment | 導入効果の定量指標 |

## 運用ワークストリーム (WS)

| 略語 | 正式名 | 説明 |
|------|--------|------|
| WS1 | Workstream 1: Adoption Bottleneck | 導入・運用ボトルネック削減。ベースライン計測シート |
| WS2 | Workstream 2: Failure Review | fail 原因の週次レビュー・再発防止 |
| WS3 | Workstream 3: Gate Exception | ゲート例外の期限付き・承認付き管理 |

## 週次メトリクス (M)

| 略語 | 正式名 | 説明 |
|------|--------|------|
| M1 | onboarding_time_minutes | 初回導入にかかる時間（分） |
| M2 | weekly_ops_time_minutes | 週次運用にかかる時間（分） |
| M3 | failure_action_coverage_rate | fail に action_owner/due_date が設定された割合 |
| M4 | gate_exception_count | status=active のゲート例外件数 |
| M5 | overdue_exceptions_count | 期限超過かつ active の例外件数 |

## Exit Criteria (C)

| 略語 | 条件 |
|------|------|
| C1 | 4 週連続で全 Exit Criteria が pass |
| C2 | 各週 overdue_exceptions_count = 0 |
| C3 | stale timestamp risk が resolved |
| C4 | 全ドキュメント・テンプレートが最新 |

## 評価スコア

| 用語 | 説明 |
|------|------|
| keyword_match_rate | 回答にドメイン固有キーワードが含まれる割合 (0-1) |
| retrieval_hit | 期待 chunk が検索結果 top-k に含まれるか (bool) |
| reference_accuracy | 回答中の引用が実際の検索結果に存在する割合 (0-1) |
| faithfulness_score | LLM Judge による根拠度スコア (0-1) |
| relevance_score | LLM Judge による質問適合度スコア (0-1) |
