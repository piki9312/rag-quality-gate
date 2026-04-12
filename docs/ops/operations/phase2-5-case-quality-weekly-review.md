# Phase2.5 Case Quality Weekly Review

ケース品質を週次で定例運用するためのチェックリストです。

## 1. Purpose

- ケースの劣化を早期検出する
- failure_category とケース改善を接続する
- 週次でケース母集団の品質を維持する

## 2. Weekly Checklist

- [ ] ケース監査ログが `runs/quality-audit/` に分離されている（`runs/quality/` と混在させない）
- [ ] 重複ケースの確認（同一意図・同一根拠）
- [ ] expected_evidence の有効性確認
- [ ] expected_keywords の過不足確認
- [ ] keyword_miss の人手レビュー（valid_failure / false_negative）
- [ ] stale case（cases.csv の last_reviewed_at から 30 日超）の抽出
- [ ] high-risk case（S1/S2）の網羅確認
- [ ] 今週の fail に対応する新規ケース追加確認

## 3. Review Log Template

| week_start | total_cases | stale_cases | duplicate_candidates | evidence_mismatch | keyword_miss_total | keyword_miss_reviewed | keyword_miss_false_negative_rate | new_cases_added | reviewer | notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| YYYY-MM-DD | 0 | 0 | 0 | 0 | 0 | 0 | 0.00 | 0 | owner-name | summary |
| 2026-03-23 | 10 | 0 | 0 | 0 | 1 | 1 | 0.00 | 0 | piki9312 | packs/hr を確認。keyword_miss 1件は valid_failure 判定。stale は last_reviewed_at 基準で算出。 |

## 3.1 Stale Rule

- stale 判定条件: `today - last_reviewed_at > 30 days`
- 対象データ項目: `packs/*/cases.csv` の `last_reviewed_at` (YYYY-MM-DD)
- `last_reviewed_at` が空欄のケースは stale 扱いとし、当週レビューで補完する

## 3.2 keyword_miss False Negative KPI

- KPI 定義:
  - false_negative_rate = false_negative_count / reviewed_keyword_miss_count
- review_verdict の値:
  - valid_failure: keyword_miss は妥当（正しく fail）
  - false_negative: 意味的には妥当回答だが語形ゆれ等で誤って fail
- 週次運用手順（例）:
  - 0) 監査ログを分離ディレクトリで更新
    - `rqg eval packs/hr/cases.csv --docs packs/hr/documents --mock --log-dir runs/quality-audit --reset-log-dir`
    - fail を含む週は終了コード 1 になるが JSONL は出力されるため、レビュー工程は継続する
  - 1) テンプレート作成
    - `python -m rqg.demo.phase2_5_keyword_miss_kpi --results-jsonl runs/quality-audit/20260330.jsonl --cases-csv packs/hr/cases.csv --export-review-csv runs/phase2-5-keyword-miss/review-20260330.csv --output runs/phase2-5-keyword-miss/summary-20260330.json`
  - 2) `review-*.csv` の `review_verdict` を記入
  - 3) KPI 集計
    - `python -m rqg.demo.phase2_5_keyword_miss_kpi --results-jsonl runs/quality-audit/20260330.jsonl --review-csv runs/phase2-5-keyword-miss/review-20260330.csv --output runs/phase2-5-keyword-miss/summary-20260330-reviewed.json --max-false-negative-rate 0.2`

## 4. Standard Actions

- duplicate_candidates > 0:
  - 重複候補を統合または用途分離し、理由を記録
- evidence_mismatch > 0:
  - expected_evidence を修正し、再実行で妥当性確認
- stale_cases > 0:
  - 優先度順に更新し、期限を設定
- keyword_miss_false_negative_rate > 0.2:
  - expected_keywords の OR 同義語候補を追加し、評価器の揺れ許容設定を見直す

## 5. Done Criteria (weekly)

- stale_cases の対応方針が記録されている
- evidence_mismatch が未放置になっていない
- 今週の failure_category に対応するケース改善が少なくとも 1 件ある

## 6. Related Files

- docs/ops/phase2-5-ws2-failure-review-template.md
- docs/ops/phase2-5-weekly-metrics-register.md
- src/rqg/demo/phase2_5_keyword_miss_kpi.py
