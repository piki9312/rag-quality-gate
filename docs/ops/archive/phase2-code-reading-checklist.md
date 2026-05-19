# Phase2 実装読解チェックリスト（30分版）

> Archive note: this is a historical Phase2 reading checklist. Use
> `docs/README.md` and `docs/strategy/current-working-set.md` for the current
> reading path.

このチェックリストは、Phase2 の実装を「運用目的 -> 実行起点 -> CLI -> コアロジック -> テスト」の順で追い、30分で説明できる状態になるためのものです。

## ゴール

次を自分の言葉で説明できること。

- Phase2 の目的は何か
- 週次 workflow が何を実行し、何で fail するか
- `migrate-cases` と `impact` がそれぞれ何をしているか
- 指標 `unresolved_legacy_refs` / `impacted_case_count` がどこで作られるか

## 30分ルート

| 時間 | 読むファイル | ここだけ押さえる |
| --- | --- | --- |
| 0-5分 | [phase2-migration-playbook.md](phase2-migration-playbook.md), [phase2-weekly-metrics-register.md](phase2-weekly-metrics-register.md) | 目的と指標（M1/M2） |
| 5-12分 | [.github/workflows/phase2-weekly-metrics.yml](../../.github/workflows/phase2-weekly-metrics.yml) | 実行シナリオと fail 条件 |
| 12-20分 | [src/rqg/cli.py](../../src/rqg/cli.py) | `cmd_migrate_cases` / `cmd_impact` の入口 |
| 20-26分 | [src/rqg/quality/case_migration.py](../../src/rqg/quality/case_migration.py), [src/rqg/quality/impact_analysis.py](../../src/rqg/quality/impact_analysis.py) | 変換ロジックと影響分析ロジック |
| 26-30分 | [tests/test_case_migration.py](../../tests/test_case_migration.py), [tests/test_impact_analysis.py](../../tests/test_impact_analysis.py) | 仕様として保証している境界条件 |

## ステップ別チェック

## 1. 目的と指標（5分）

- [ ] [phase2-migration-playbook.md](phase2-migration-playbook.md) で Phase2 の目的を確認した
- [ ] M1=`impacted_case_count` と M2=`unresolved_legacy_refs` の定義を確認した
- [ ] [phase2-weekly-metrics-register.md](phase2-weekly-metrics-register.md) の `decision` 列（`keep-going` / `investigate`）を確認した

確認メモ:

- M1 の目標:
- M2 の目標:
- investigate に切り替える条件:

## 2. Workflow 起点（7分）

- [ ] [.github/workflows/phase2-weekly-metrics.yml](../../.github/workflows/phase2-weekly-metrics.yml) の `Collect phase2 metrics` を読んだ
- [ ] `migrate-cases` 実行箇所を特定した
- [ ] `impact` 実行箇所を特定した
- [ ] `summary.json` に何を書いているか確認した
- [ ] fail 条件（2つ）を確認した
        
確認メモ:

- 生成する summary 項目:
- fail 条件1:
- fail 条件2:

## 3. CLI 入口（8分）

- [ ] [src/rqg/cli.py](../../src/rqg/cli.py) の `cmd_migrate_cases` を読んだ
- [ ] [src/rqg/cli.py](../../src/rqg/cli.py) の `cmd_impact` を読んだ
- [ ] それぞれが呼ぶ core 関数をメモした

確認メモ:

- migrate-cases が呼ぶ関数:
- impact が呼ぶ関数:
- どの出力ファイルを作るか:

## 4. コアロジック（6分）

### 4-1. case migration

- [ ] [src/rqg/quality/case_migration.py](../../src/rqg/quality/case_migration.py) の `migrate_expected_evidence` を読んだ
- [ ] `source_path -> doc_id` マッピング生成を理解した
- [ ] `unresolved_legacy_refs` が増える条件を理解した

### 4-2. impact analysis

- [ ] [src/rqg/quality/impact_analysis.py](../../src/rqg/quality/impact_analysis.py) の `detect_changed_evidence_ids` を読んだ
- [ ] `extract_impacted_cases` でケースを絞る条件を理解した
- [ ] `build_impact_report` の最終出力を確認した

確認メモ:

- changed_evidence_ids の作り方:
- impacted_case_ids の作り方:

## 5. テストで仕様固定（4分）

- [ ] [tests/test_case_migration.py](../../tests/test_case_migration.py) を読んだ
- [ ] [tests/test_impact_analysis.py](../../tests/test_impact_analysis.py) を読んだ
- [ ] 正常系と異常系を1つずつ説明できる

確認メモ:

- migration 正常系:
- migration 異常系:
- impact 正常系:
- impact 異常系:

## 最終チェック（説明できれば完了）

次の文章を 60 秒で説明できれば完了です。

"Phase2 は legacy 参照の段階的削減フェーズで、週次 workflow が `migrate-cases` と `impact` を実行して、`unresolved_legacy_refs == 0` と `impacted_case_count > 0` を継続確認する。逸脱時は `investigate` へ切り替える。"

## つまずいた時の逆引き

- `unresolved_legacy_refs` の意味が曖昧:
  [src/rqg/quality/case_migration.py](../../src/rqg/quality/case_migration.py)
- `impacted_case_count` の算出元が不明:
  [src/rqg/quality/impact_analysis.py](../../src/rqg/quality/impact_analysis.py)
- どのタイミングで fail するか不明:
  [.github/workflows/phase2-weekly-metrics.yml](../../.github/workflows/phase2-weekly-metrics.yml)
