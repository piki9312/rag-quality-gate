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
- `change-event.yml` (docs/model/prompt/retrieval/config change)
- manual review file (必要時)

`change-event.yml` は、今回の変更を release review に渡すための最小入力です。FAQ更新、規約変更、料金表変更、プロンプト変更、モデル変更、retriever設定変更のときに使います。安全な雛形は [templates/change-event.example.yml](../../templates/change-event.example.yml) です。

安全上の注意:

- 顧客名、実在文書名、絶対パス、内部 release 名、customer-specific summary を書きすぎない
- CI-safe artifact には raw asset name / raw document name / path / target_release を出さない
- safe 版では hash / count / bounded metadata のみを使う
- full metadata は local / private runner / customer-controlled 環境のみ
- sanitizer に頼らず、入力時点で最小情報にする

## 4. 実行手順

1. `rqg doctor`
2. `rqg validate-pack --pack . --strict-s1-governance`
3. 外部RAGなら `rqg validate-connection ...`
4. 変更内容を `change-event.yml` に記述する
5. `rqg gate --pack . --customer-facing --strict-s1-governance --change-event change-event.yml ...`
6. 必要なら `rqg check --log-dir <existing logs> --change-event change-event.yml`
7. Dashboard で Change Event Card を確認する
8. Dashboard の Production Readiness Card / warning を確認する
9. Report Preview の Change Summary を顧客提出前に確認する
10. `customer-summary.md`, `gate-report.md`, `gate-decision.json`, `gate-report.json` を確認
11. NEEDS_REVIEW / S1 / fallback があれば manual review を記録
12. 変更前比較が必要なら `--baseline-bundle <previous gate-report.json>`
13. decision meeting で release / block / follow-up を決める

最小コマンド例:

```powershell
rqg gate --change-event change-event.yml
rqg check --change-event change-event.yml
```

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
