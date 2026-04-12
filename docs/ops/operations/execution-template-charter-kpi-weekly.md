# 実行用テンプレート（憲章 + KPI + 週次レビューシート）

このテンプレートは、RAG/Agent を安全に更新・運用するための品質ゲート基盤を、
実装だけでなく運用として継続するための実行フォーマットです。

---

## 1. 憲章テンプレート（Product Charter）

### 1-1. プロダクト定義

- プロダクト名:
- 一言定義:
  - 例: AI を賢くするのではなく、AI を安全に更新・運用できるようにする品質管理レイヤ

### 1-2. 解決する課題

- 対象変更:
  - 文書更新
  - モデル変更
  - プロンプト変更
  - retrieval 変更
  - ツール変更
- 起きる問題:
- 失敗時の事業インパクト:

### 1-3. 提供価値

- 何を防ぐか:
- 何を可視化するか:
- 何を自動化するか:

### 1-4. スコープ

- In Scope:
  - ingest
  - snapshot
  - case
  - eval
  - gate
  - impact
  - review
  - CI 連携
- Out of Scope:
  - モデル自体の精度改善
  - 生成品質の主観的最適化のみを目的とした改修

### 1-5. フェーズ定義

- Phase 1: 最小品質ゲート成立
- Phase 1.5: 人が回せる運用導線
- Phase 2: 導入障壁を下げる
- Phase 2.5: 実運用で壊れにくくする
- Phase 3: Pack として売れる形
- Phase 4: 実績化

### 1-6. 現在地と直近ゴール

- 現在地:
- 直近 2 週間のゴール:
- このゴールを達成したと判断する条件:

### 1-7. 意思決定原則

- 原則1: 品質ゲートとしての安全性を優先する
- 原則2: 運用で回ることを優先する
- 原則3: 再現性のない改善は採用しない

### 1-8. 実装優先順位（固定）

1. 品質ゲートとしての核を壊さない
2. 導入障壁を下げる
3. 実運用で嫌われないようにする
4. fail から改善につながるループを強化する
5. Pack 化・有償 PoC 化・将来 SaaS 化につながる形で整理する

### 1-9. いま優先しないこと（固定）

- AI アプリ本体の機能拡張
- 不要に大きい UI 化
- 早すぎる SaaS インフラ実装
- 何でも対応しようとする入力媒体の一般化
- 本質価値に直結しない機能追加

### 1-10. Issue / PR 判断短文テンプレート

- This change improves safe update/operation of the quality gate, not model intelligence itself.
- Scope stays in document-diff quality gate for this phase.
- Legacy compatibility remains temporary and removable.

---

## 2. KPI テンプレート

### 2-1. North Star

- North Star KPI:
- 定義:
- 目標値:
- 測定頻度:

### 2-2. 運用 KPI 一覧

| KPI ID | KPI 名 | 定義 | 計算方法 | データソース | 目標 | 閾値（Warn/Fail） | オーナー | 更新頻度 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| K1 | Gate pass rate | eval/check の通過率 | pass runs / total runs | runs/quality | >= 95% | warn < 95, fail < 90 |  | weekly |
| K2 | impacted_case_count | 影響ケース件数 | len(impact_report.impacted_case_ids) | impact report JSON | 想定レンジ内 | warn: 急増 |  | weekly |
| K3 | unresolved_legacy_refs | 移行未解決件数 | migration_report.unresolved_legacy_refs | migration report JSON | 0 | fail > 0 |  | weekly |
| K4 | impact stability | impact での影響安定性 | impacted_case_ids 件数推移 | impact report | 変動許容内 | warn: 急増 |  | weekly |
| K5 | MTTR for gate fail | gate fail から復旧まで | 復旧時刻 - fail 時刻 | PR/CI log | <= X 日 | warn > X |  | weekly |

### 2-3. KPI 収集コマンド（例）

1. impact

- qgate impact --old-snapshot <old> --new-snapshot <new> --cases <cases> --output <impact.json>

2. migrate-cases

- rqg migrate-cases --cases <cases> --snapshot <snapshot> --snapshot-dir <snapshot_dir> --output <migrated_cases> --report <migration_report.json>

3. eval/check

- rqg eval <cases.csv> --docs <docs_dir> --mock --index-dir index --log-dir runs/quality
- rqg check --log-dir runs/quality --config .rqg.yml

---

## 3. 週次レビューシートテンプレート

### 3-1. ヘッダ

- Week:
- 期間:
- 参加者:
- ファシリテーター:
- 記録者:

### 3-2. 先週アクションの結果

| アクション | 担当 | 期限 | 結果 | ステータス |
| --- | --- | --- | --- | --- |
|  |  |  |  | done / carry-over / blocked |

### 3-3. KPI レビュー

| KPI | 先週値 | 今週値 | 差分 | 判定（Green/Yellow/Red） | コメント |
| --- | ---: | ---: | ---: | --- | --- |
| Gate pass rate |  |  |  |  |  |
| impacted_case_count |  |  |  |  |  |
| unresolved_legacy_refs |  |  |  |  |  |
| impact stability |  |  |  |  |  |
| MTTR for gate fail |  |  |  |  |  |

### 3-4. インシデント / 失敗分析

| 日付 | 種別 | 事象 | 影響 | 原因分類 | 再発防止アクション | 担当 | 期限 |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  | retrieval miss / stale / synthesis / tool failure / others |  |  |  |  |  |  |

### 3-5. 互換削減トラッキング（Phase2 用）

| case_source | owner | baseline impacted | current impacted | unresolved refs | target_zero_date | 今週の進捗 |
| --- | --- | ---: | ---: | ---: | --- | --- |
|  |  |  |  |  |  |  |

### 3-6. 意思決定ログ

| 議題 | 判断 | 理由 | 影響範囲 | 次回見直し日 |
| --- | --- | --- | --- | --- |
|  | Go / No-Go / Hold |  |  |  |

### 3-7. 来週アクション

| 優先度 | アクション | 担当 | 期限 | 成功条件 |
| --- | --- | --- | --- | --- |
| P0 |  |  |  |  |
| P1 |  |  |  |  |
| P2 |  |  |  |  |

---

## 4. フェーズ移行ゲートテンプレート

### Phase 1 -> 1.5

- [ ] fail -> fix -> pass が再現できる
- [ ] ingest, eval, check が通しで運用できる

### Phase 1.5 -> 2

- [ ] README だけで導入再現できる
- [ ] impact + review + migrate-cases の導線がある
- [ ] legacy 依存量が可視化できる

### Phase 2 -> 2.5

- [ ] 導入障壁の主要ボトルネックが改善
- [ ] 運用時の fail 原因が分類できる
- [ ] ゲート形骸化対策が定義済み

### Phase 2.5 -> 3

- [ ] Pack として提供する最小構成が定義済み
- [ ] 1 ジョブ追加で導入可能な説明が成立

### Phase 3 -> 4

- [ ] 少なくとも 1 ユースケースで継続運用実績
- [ ] 週次運用の成果指標が示せる

---

## 5. 運用原則（貼り付け用）

このプロジェクトは、AI を賢くするものではない。
AI を安全に更新・運用できるようにする品質ゲートを作るものである。
