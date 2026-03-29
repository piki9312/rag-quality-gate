# Phase2.5 Case Quality Weekly Review

ケース品質を週次で定例運用するためのチェックリストです。

## 1. Purpose

- ケースの劣化を早期検出する
- failure_category とケース改善を接続する
- 週次でケース母集団の品質を維持する

## 2. Weekly Checklist

- [ ] 重複ケースの確認（同一意図・同一根拠）
- [ ] expected_evidence の有効性確認
- [ ] expected_keywords の過不足確認
- [ ] stale case（更新から 30 日超）の抽出
- [ ] high-risk case（S1/S2）の網羅確認
- [ ] 今週の fail に対応する新規ケース追加確認

## 3. Review Log Template

| week_start | total_cases | stale_cases | duplicate_candidates | evidence_mismatch | new_cases_added | reviewer | notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| YYYY-MM-DD | 0 | 0 | 0 | 0 | 0 | owner-name | summary |
| 2026-03-23 | 10 | 0 | 0 | 0 | 0 | piki9312 | packs/hr のケースを確認。WS2 failure row は 0 件、追加ケースは不要。stale 判定用 timestamp 列は未整備のため暫定 0 扱い。 |

## 4. Standard Actions

- duplicate_candidates > 0:
  - 重複候補を統合または用途分離し、理由を記録
- evidence_mismatch > 0:
  - expected_evidence を修正し、再実行で妥当性確認
- stale_cases > 0:
  - 優先度順に更新し、期限を設定

## 5. Done Criteria (weekly)

- stale_cases の対応方針が記録されている
- evidence_mismatch が未放置になっていない
- 今週の failure_category に対応するケース改善が少なくとも 1 件ある

## 6. Related Files

- docs/ops/phase2-5-ws2-failure-review-template.md
- docs/ops/phase2-5-weekly-metrics-register.md
