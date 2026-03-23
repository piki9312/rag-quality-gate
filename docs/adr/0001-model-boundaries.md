# ADR 0001: Model Boundaries For Phase 1 Quality Gate

## Status

Accepted

## Context

Phase 1 で以下のドメインモデルを追加した。

- `DocumentSnapshot`
- `EvalCase`
- `GateDecision`

同時に、既存システムには以下の実装寄りモデルが存在する。

- `QATestCase`
- `EvalResult`
- `EvalRun`
- `QARunRecord`

このまま進めると、以下が混ざりやすい。

- ドメイン判断用モデル
- runner 内部の実行用モデル
- 永続化用モデル
- CLI 入出力用のファイル表現

今回は全面再設計ではなく、今後の実装で迷わないために責務の境界だけ先に固定する。

## Decision

### 1. Domain models are the canonical business concepts

`src/rqg/domain/` は、品質ゲート基盤として外部に説明できる概念を表す。

- `DocumentSnapshot`
  - 文書のある時点のスナップショット
  - ingest の結果として扱う
  - JSON ファイル保存や将来の DB 保存の主対象
- `EvalCase`
  - 評価対象としてのケース定義
  - runner に流し込む前の、品質管理上の単位
- `GateDecision`
  - ゲート判定の結果
  - check 実行後に残すべき最終判断

これらは「何を管理したいか」を表すモデルであり、「どう実行したか」の詳細は持たない。

### 2. `quality.models` are execution and persistence support models

`src/rqg/quality/models.py` の既存モデルは当面維持するが、役割を以下に限定する。

- `QATestCase`
  - 既存 runner が直接消費する入力モデル
  - CSV 由来の実行用アダプタ
  - ドメイン上の正本ではない
- `EvalResult`
  - 単一ケースの実行結果
  - 実行時メトリクスや失敗理由を持つランタイムモデル
- `EvalRun`
  - 複数 `EvalResult` の集約
  - 実行単位のランタイムモデル
- `QARunRecord`
  - JSONL 永続化専用モデル
  - ログ読込と gate 判定の入力

要するに `quality.models` は「runner/check を動かすための実装モデル」であり、ドメインモデルの代替にはしない。

### 3. Persistence models stay separate from domain models

`QARunRecord` は永続化用のレコードモデルとして残す。

理由:

- `EvalResult` のまま JSONL に落とす責務とは異なる
- ログの後方互換を保ちやすい
- gate 集計で必要な情報だけを絞り込める

一方で:

- `DocumentSnapshot` は現時点ではそのまま JSON 保存してよい
- `GateDecision` も現時点ではそのまま JSON 保存してよい

これは Phase 1 では十分だが、将来ストレージ要件が増えたら専用 record を追加してよい。

### 4. CLI files are transport representations, not new domain types

CLI が扱う JSON / CSV / JSONL はファイル形式であり、別の概念モデルではない。

- `init-snapshot` の JSON は `DocumentSnapshot` のシリアライズ結果
- `create-sample-case` の JSON は `EvalCase` のシリアライズ結果
- `create-sample-gate` と `check --decision-file` の JSON は `GateDecision` のシリアライズ結果
- `cases.csv` は既存運用との互換のための入力形式
- `*.jsonl` は `QARunRecord` の保存形式

CLI はモデルを読み書きする境界であって、独自の業務ロジックを持たない。

### 5. Adapters are the approved bridge

既存 runner をすぐには置き換えないため、橋渡しはアダプタ関数で行う。

- `load_eval_cases()`
- `eval_case_to_qa_test_case()`
- `qa_test_case_to_eval_case()`
- `build_gate_decision()`

方針:

- runner を直接 `EvalCase` ネイティブに作り替えるのは後続タスク
- 今回は変換点を明示し、責務の混線を防ぐ

## Consequences

### Good

- ドメイン概念と実行内部表現を分けて説明できる
- 既存 runner/check の破壊を避けられる
- 将来 `QATestCase` を縮退または置換しやすい

### Trade-offs

- 一時的にモデルが並存する
- 変換コードが増える

ただし Phase 1 では、この重複は安全な移行コストとして許容する。

## Non-goals

今回やらないこと:

- `quality.models` の全面廃止
- runner の全面ドメインモデル化
- JSONL 形式の刷新
- DB スキーマ設計
- 複数レイヤの抽象 base class 導入

## Practical Rules

今後の実装では以下を守る。

1. 新しい業務概念はまず `src/rqg/domain/` に置く。
2. runner の都合だけで必要なものは `src/rqg/quality/models.py` に置く。
3. 永続化専用の形は record/model を分ける。
4. CLI コマンドは domain model か record model の読み書きに徹し、独自の状態を増やさない。
5. 既存 `QATestCase` を使う箇所に domain model を入れるときは、まずアダプタを経由する。
