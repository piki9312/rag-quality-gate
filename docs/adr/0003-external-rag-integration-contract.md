# ADR 0003: External RAG Integration Contract

## Title

External RAG Integration Contract

## Status

Proposed

## Date

2026-04-20

## Context

RQG は現在、ローカルの `RAGStore` を用いた ingest / retrieval / eval の参照実装を持っている。一方で、今後の主な利用形態は「既存の外部 RAG システムの上に載る品質レイヤ」に寄っていく。

この変化により、以下がぶれやすくなっている。

- core が具体的な RAG 実装に依存するのか、 retrieval 契約に依存するのか
- ベンダーごとに異なる retrieval レスポンスをどこで吸収するのか
- `search` と `search_multi` を何の意味で使い分けるのか
- `score` を gate や判定ロジックにどこまで使ってよいのか
- timeout / auth / external 5xx / schema mismatch を品質失敗とどう切り分けるのか

今の runner は `chunk_id`, `source`, `text`, `score` を持つ検索結果を前提にしており、この最小契約が外部接続でも維持されないと eval / check / gate の責務境界が崩れる。

## Decision

### 1. Core は具体的な RAG 実装ではなく retrieval 契約に依存する

RQG core は、特定ベンダー SDK や特定検索エンジンのレスポンス形に直接依存しない。

今後の統合点は、実装上は `RAGStoreProtocol` 相当の契約として扱う。

最小責務は以下とする。

- `search(query, top_k)`
  - 単一クエリでの retrieval を実行する
  - relevance 順の `RetrievedChunk` 列を返す
- `search_multi(query, top_k)`
  - 同一質問意図に対する multi-query retrieval を実行する
  - relevance 順の `RetrievedChunk` 列を返す

この ADR は契約を固定するものであり、直ちにすべての呼び出し箇所を Protocol 化することまでは決めない。

### 2. Adapter 層が外部レスポンス差分を吸収する

外部 RAG との接続では、 adapter が以下を担う。

- vendor 固有レスポンスから `RetrievedChunk` への正規化
- auth / endpoint / timeout / retry 設定の管理
- vendor 固有の例外を RQG の評価可能なエラー種別に正規化
- `search_multi` の実装差を core に漏らさない
- logging 時に secret や認証情報を漏らさない

RQG core は adapter の外側で、 raw vendor payload を解釈しない。

### 3. `RetrievedChunk` の最小契約を固定する

外部 RAG との最小 I/O 契約は以下とする。

- `chunk_id`
  - retrieval 結果内で一意な識別子
  - `expected_evidence` や `retrieved_ids` と照合できること
- `source`
  - 人間が出所を把握できる識別子
  - file path, document key, URL, doc title などを許容する
- `text`
  - 評価対象の実テキスト
  - answer generation と judge の両方に使えること
- `score`
  - retrieval 順序の補助値
  - `float` または `null` を許容する

この契約の限界も明示する。

- `chunk_id` が stable でない外部系では、 evidence 照合は脆くなる
- `source` は説明補助であり、 evidence の正本ではない
- `text` だけでは doc lineage や snapshot lineage は十分に表現できない
- `score` は retrieval 補助値であり、品質判定の正本ではない

### 4. `score` は補助値であり厳密比較前提にしない

`score` は以下の用途に限定する。

- 同一レスポンス内での順位補助
- debug / review 時の参考情報
- adapter 内での merge / dedupe の補助

`score` を以下には使わない。

- ベンダー間の厳密比較
- 異なる index version 間の品質比較
- gate の pass/fail 直接判定
- `expected_evidence` との一致判定の代替

RQG の品質判定は、引き続き `retrieved_ids`, `expected_evidence`, answer, judge score, keyword score を主とする。

### 5. `search` と `search_multi` の意味を明文化する

`search` は、単一の user question をそのまま retrieval にかける経路とする。

`search_multi` は、同一の user question に対して query expansion, keywordization, hybrid retrieval, vendor native multi-query などを用いて候補を広げ、その結果を同一の `RetrievedChunk` 契約に正規化して返す経路とする。

`search_multi` に関して固定する原則は以下とする。

- 入力の質問意図を変えない
- adapter 内で dedupe 済み、または dedupe 可能な結果を返す
- 出力型は `search` と同一にする
- multi-query であることを core の評価意味に持ち込まない

RQG core は `search_multi` を「より広い retrieval strategy」としてのみ扱い、別評価モードにはしない。

### 6. エラーは品質失敗ではなく接続失敗として正規化する

外部接続時の代表的な失敗は以下のように扱う。

- schema mismatch / required field missing / incompatible payload
  - `CONFIG_ERROR`
- timeout / connection error / auth failure / 429 / external 5xx
  - `INFRA_ERROR`
- empty result
  - 正常な retrieval 結果のひとつとして扱う
  - 自動的に config error にはしない

adapter は vendor 例外をこの分類へ正規化して runner / report / support へ渡す。

## Consequences

### Good

- RQG core が外部 RAG ベンダー差分から切り離される
- adapter ごとに schema 差分や auth 差分を閉じ込められる
- retrieval miss と integration failure を report 上で分離しやすくなる
- ローカル `RAGStore` を参照実装として残しつつ、外部接続へ移行しやすくなる

### Trade-offs

- adapter 実装とテストの保守コストが増える
- vendor 固有 metadata をすぐには core に持ち込めない
- `score` の活用は意図的に制限される
- `chunk_id` 安定性が弱い外部系では、 evidence 照合の品質が adapter 設計に強く依存する

## Alternatives Considered

### 1. `RAGStore` 具体実装に依存し続ける

却下。

この方針では、外部 RAG を接続するたびに runner や serving layer へ vendor 依存が漏れ、責務境界が壊れる。

### 2. raw vendor payload をそのまま runner に渡す

却下。

この方針では、 adapter 境界が無意味になり、 report / support / test が vendor ごとに分岐する。

### 3. 最初から `doc_id`, `snapshot_id`, metadata を必須契約にする

今回は見送る。

将来有用だが、初期の external RAG 接続では過剰拘束になりやすい。

## Open Questions

- `RetrievedChunk` に `metadata`, `doc_id`, `snapshot_id` をいつ追加するか
- adapter ごとの timeout / retry の標準値を repo で持つか
- `search_multi` の provenance を debug 用にどこまで保持するか
- `chunk_id` と `expected_evidence` の互換性を保つ migration 手段を標準化するか
- answer generation 自体も外部システム側に委譲する場合、 retrieval 契約と answer 契約をどう分けるか