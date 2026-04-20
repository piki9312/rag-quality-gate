# ADR 0008: RQG Scope And Non-goals

## Title

RQG Scope And Non-goals

## Status

Proposed

## Date

2026-04-20

## Context

RQG repo は当初、ローカル RAG 実装を同梱した quality gate ツールとして育ってきた。現在は external RAG integration の必要性が高まり、 repo の中心は「RAG エンジン本体」ではなく「品質評価 / check / gate / quality asset governance」を担う層へ移っている。

この移行期では、 scope を固定しないと以下が起きる。

- repo が RAG engine 本体の backlog まで抱え込む
- 会社全体の事業戦略や GTM が repo ADR に混ざる
- local reference implementation と product boundary が混同される
- 実装判断と上位戦略文書の役割分担が壊れる

## Decision

### 1. RQG repo の主責務を quality layer として固定する

RQG repo が担うのは以下とする。

- `eval`, `check`, `gate` の実行と判定
- quality report と gate decision の出力
- `cases.csv` を中心とする quality asset governance
- `review.csv`, merge, validate, impact などの補助ワークフロー
- external system との接続契約と adapter 境界
- repo 内で再現可能な reference harness と testability

RQG は「品質を観測し、判定し、改善サイクルを回すレイヤ」である。

### 2. RAG engine 本体は scope 外とする

以下は repo の主責務に含めない。

- production retrieval engine の開発
- production chunking / indexing platform の提供
- vector DB / ANN infra のプロダクト化
- LLM hosting / model serving
- 業務アプリ本体の UX / workflow

repo にローカル `RAGStore` や ingest が存在しても、それは reference implementation と development harness として扱う。

### 3. repo ADR は実装と運用に効く範囲に絞る

repo 内の ADR は、以下に直接効くものに限定する。

- code structure
- schema contract
- adapter boundary
- cases / review / merge / validate policy
- gate / eval / check semantics
- support / operations boundary

以下は repo ADR の対象外とする。

- 会社全体の GTM
- pricing
- sales positioning
- AI Quality Infrastructure 全体戦略
- 全社レベルの portfolio strategy

これらは上位の product / strategy 文書で扱う。

### 4. 今の repo は RAG を対象とするが、設計原則は将来拡張を妨げない

現在の主対象は RAG quality である。

ただし、以下の原則は将来の拡張を阻害しないように保つ。

- core は契約に依存する
- quality asset は governed source of truth を持つ
- quality failure と infra failure を分ける
- review 補助と確定資産を分ける

将来 Agent や他の AI system に対象が広がっても、 repo の主責務は quality layer に留める。

### 5. local RAG 実装は product identity ではなく reference harness とする

repo にある local FAISS / embedding / ingest 実装は、以下の役割で維持する。

- quickstart
- demo
- CI / test
- mock / fallback 付きの再現可能な eval path

これは「RQG が自前 RAG プラットフォームを主製品として提供する」という意味ではない。

## Consequences

### Good

- repo の判断基準がぶれにくくなる
- external RAG support を追加しても product identity が崩れない
- ADR が実装と運用に直結しやすくなる
- 上位戦略文書と repo 設計文書の役割分担が明確になる

### Trade-offs

- RAG engine や hosting に関する要望を repo で受けきれなくなる
- local reference implementation の位置づけを丁寧に説明する必要がある
- 一部の platform 化要求は別リポジトリや別文書へ切り出す必要がある

## Alternatives Considered

### 1. RQG repo を end-to-end AI platform まで拡張する

却下。

repo の責務が広がりすぎ、 quality gate と governance の判断が鈍る。

### 2. repo 内に戦略 ADR も混在させる

却下。

実装判断と事業判断の更新周期が異なる。

### 3. local RAG 実装をただちに除去する

今回は採らない。

quickstart, demo, testability の観点で、 reference harness は依然として有用である。

## Open Questions

- external adapter が主流になった後、 local ingest / RAGStore を別 package に切り出すか
- Agent / tool-use evaluation を repo scope に含めるか、別 repo に切るか
- repo 外の strategy 文書との参照関係をどう管理するか
- support / operation guide のうち repo 直結部分をどこまで docs に含めるか