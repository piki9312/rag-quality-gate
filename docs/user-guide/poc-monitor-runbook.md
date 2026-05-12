# Proof Gate PoC / Monitor Runbook

## 1. 対象シナリオ

- 外部RAG APIを持つベンダー案件
- 既存AIチャットボットを持つエンド企業案件
- FAQ / 規約 / 料金表更新後の Monitor 案件

## 2. 事前確認

- 対象AIの実行経路が local / external のどちらか確定している
- 顧客向け成果物は `customer-summary.md` を主に使う
- `mock` はデモ専用であり、顧客品質証跡に使わない
- S1ケースは owner / last_reviewed_at / expected_answer / expected_evidence / `manual_review_required` を満たす

## 3. 必要入力

- `cases.csv`
- `gate.yml`
- `quality-pack.yml`
- `documents/` または `adapter/adapter_config.yml`
- change event file (docs/model/prompt/retrieval/config change)
- manual review file (必要時)

## 4. 実行手順

1. `rqg doctor`
2. `rqg validate-pack --pack . --strict-s1-governance`
3. 外部RAGなら `rqg validate-connection ...`
4. `rqg gate --pack . --customer-facing --strict-s1-governance ...`
5. `customer-summary.md`, `gate-report.md`, `gate-decision.json`, `gate-report.json` を確認
6. NEEDS_REVIEW / S1 / fallback があれば manual review を記録
7. 変更前比較が必要なら `--baseline-bundle <previous gate-report.json>`
8. decision meeting で release / block / follow-up を決める

## 5. decision meeting で確認すること

- execution_mode
- 対象文書 / 対象ケース / 対象モデル / 対象設定
- S1失敗、NEEDS_REVIEW、fallback
- before-after の newly failing / recovered / unchanged failures
- manual review / approval scope
- 顧客に約束してよい範囲

## 6. Follow-up

- false positive / false negative を記録する
- cases / taxonomy / source documents / prompt constraints の更新要否を決める
- 次回 Monitor の change_event と linked run を残す
