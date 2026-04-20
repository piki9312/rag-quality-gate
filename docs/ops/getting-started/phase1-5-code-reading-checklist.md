# Phase1.5 実装読解チェックリスト（30分版）

このチェックリストは、Phase1.5 の実装を「運用目的 -> デモ起点 -> CLI -> コアロジック -> テスト」の順で追い、30分で説明できる状態になるためのものです。

## ゴール

次を自分の言葉で説明できること。

- Phase1.5 の目的は何か
- `impact` が何を比較して、何を `impacted_case_ids` に入れるか
- fail -> fix -> pass の運用導線で `impact` がどこに効くか
- strict モードで path 参照と doc_id 参照がどう扱われるか

## 30分ルート

| 時間 | 読むファイル | ここだけ押さえる |
| --- | --- | --- |
| 0-5分 | [execution-template-charter-kpi-weekly.md](execution-template-charter-kpi-weekly.md), [impact-cycle.md](../demo/impact-cycle.md) | Phase1.5 の定義と期待フロー |
| 5-12分 | [src/rqg/demo/impact_cycle.py](../../src/rqg/demo/impact_cycle.py) | pass -> fail -> pass の再現シナリオ |
| 12-18分 | [src/rqg/cli/__init__.py](../../src/rqg/cli/__init__.py), [src/rqg/cli/casegen.py](../../src/rqg/cli/casegen.py) | `cmd_impact` と関連コマンドの入口 |
| 18-26分 | [src/rqg/quality/impact_analysis.py](../../src/rqg/quality/impact_analysis.py), [src/rqg/domain/impact_report.py](../../src/rqg/domain/impact_report.py), [src/rqg/presentation/markdown/impact_report_review.py](../../src/rqg/presentation/markdown/impact_report_review.py) | 差分検出・影響抽出・出力構造 |
| 26-30分 | [tests/test_impact_analysis.py](../../tests/test_impact_analysis.py) | 仕様として固定している境界条件 |

## ステップ別チェック

## 1. 目的と期待フロー（5分）

- [ ] [execution-template-charter-kpi-weekly.md](execution-template-charter-kpi-weekly.md) の Phase 1.5 定義を確認した
- [ ] [impact-cycle.md](../demo/impact-cycle.md) の期待ステータス `phase1_gate=pass -> phase2_gate=fail -> phase3_gate=pass` を確認した
- [ ] なぜ Phase1 だけでは不十分で、Phase1.5 で `impact` が必要か説明できる

確認メモ:

- Phase1.5 の一言定義:
- impact が必要な理由:

## 2. デモ起点（7分）

- [ ] [src/rqg/demo/impact_cycle.py](../../src/rqg/demo/impact_cycle.py) の `run_demo` を読んだ
- [ ] Phase1 / Phase2 / Phase3 で何を壊して何を直しているか確認した
- [ ] `summary.json` に残る項目を確認した
- [ ] どの条件で RuntimeError にしてデモ失敗にするか確認した

確認メモ:

- Phase2 で fail させる条件:
- Phase3 で pass に戻す条件:
- summary に残す主要フィールド:

## 3. CLI 入口（6分）

- [ ] [src/rqg/cli/casegen.py](../../src/rqg/cli/casegen.py) の `cmd_impact` を読んだ
- [ ] [src/rqg/cli/casegen.py](../../src/rqg/cli/casegen.py) の `cmd_gen_cases` を読んだ
- [ ] `--review-output` が有効なときの挙動を確認した
- [ ] 例外時のエラーメッセージ境界（snapshot/cases/build 失敗）を確認した

確認メモ:

- `cmd_impact` が呼ぶコア関数:
- 標準出力に出す件数:
- 出力ファイル:

## 4. コアロジック（8分）

### 4-1. 差分検出

- [ ] [src/rqg/quality/impact_analysis.py](../../src/rqg/quality/impact_analysis.py) の `detect_changed_evidence_ids` を読んだ
- [ ] section hash 比較で changed_evidence_ids を作る流れを理解した

### 4-2. 影響ケース抽出

- [ ] [src/rqg/quality/impact_analysis.py](../../src/rqg/quality/impact_analysis.py) の `extract_impacted_cases` を読んだ
- [ ] strict モードで `expected_evidence` と changed セットを突き合わせる条件を理解した
- [ ] [src/rqg/domain/impact_report.py](../../src/rqg/domain/impact_report.py) の `ImpactReport` フィールドを確認した
- [ ] [src/rqg/presentation/markdown/impact_report_review.py](../../src/rqg/presentation/markdown/impact_report_review.py) のレビュー出力を確認した

確認メモ:

- changed_evidence_ids の算出単位:
- impacted_case_ids への追加条件:
- details に残る情報:

## 5. テストで仕様固定（4分）

- [ ] [tests/test_impact_analysis.py](../../tests/test_impact_analysis.py) を読んだ
- [ ] 正常系（changed + impacted 検出）を1つ説明できる
- [ ] 異常系（不正 snapshot/cases 入力）を1つ説明できる
- [ ] strict モードの互換境界（doc_id は一致、path は非一致）を説明できる

確認メモ:

- 正常系テスト:
- 異常系テスト:
- strict 境界テスト:

## 最終チェック（説明できれば完了）

次の文章を 60 秒で説明できれば完了です。

"Phase1.5 は fail を見つけるだけでなく、変更差分に紐づく影響ケースへレビュー対象を絞るフェーズで、`impact` が `changed_evidence_ids` と `impacted_case_ids` を生成し、fail -> fix -> pass の運用判断を人が回せる形にする。"

## つまずいた時の逆引き

- `impact` の入口と引数が曖昧:
  [src/rqg/cli/__init__.py](../../src/rqg/cli/__init__.py), [src/rqg/cli/casegen.py](../../src/rqg/cli/casegen.py)
- changed/impacted の算出ロジックが曖昧:
  [src/rqg/quality/impact_analysis.py](../../src/rqg/quality/impact_analysis.py)
- 出力 JSON の構造が曖昧:
  [src/rqg/domain/impact_report.py](../../src/rqg/domain/impact_report.py)
- レビュー用 Markdown の見え方が曖昧:
  [src/rqg/presentation/markdown/impact_report_review.py](../../src/rqg/presentation/markdown/impact_report_review.py)
