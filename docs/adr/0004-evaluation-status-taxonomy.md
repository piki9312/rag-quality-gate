# ADR 0004: Evaluation Status Taxonomy

## Title

Evaluation Status Taxonomy

## Status

Proposed

## Date

2026-04-20

## Context

RQG には現在、 eval の結果、 check の閾値判定、 gate の pass / warn / fail、 review.csv の補助状態、 cases.csv の `active / draft / needs_review / deprecated` が併存している。

外部 RAG 対応が進むにつれて、以下が混ざりやすくなった。

- 品質問題
- 接続問題
- 設定不整合
- review 未確定状態
- 意図的な除外や skip

この状態のままだと、 report で「何が起きたか」は見えても、「誰が何を直すか」が曖昧になる。特に external RAG では timeout, auth, 5xx を品質 fail と同列に扱うと運用が荒れる。

一方で、既存 gate の意味は壊したくない。現在の運用は `pass / warn / fail` を前提に CI や日次運用が組まれている。

## Decision

### 1. RQG の canonical な評価状態を以下に整理する

- `PASS`
  - 要求された評価条件を満たした
- `WARN`
  - 品質懸念または要観察事項はあるが、直ちに block しない
- `QUALITY_FAIL`
  - retrieval, answer quality, evidence, citation, judge の観点で基準未達
- `INFRA_ERROR`
  - timeout, auth failure, external 5xx, rate limit, adapter availability など
- `CONFIG_ERROR`
  - contract mismatch, invalid config, invalid schema, incompatible adapter mapping など
- `REVIEW_REQUIRED`
  - ケースや補助生成物が未確定で、人手判断が必要
- `SKIPPED`
  - 意図的に評価対象から外した、または実行対象外だった

### 2. 既存 gate の `pass / warn / fail` は維持する

この ADR は gate の公開意味を刷新しない。

外部公開の gate 出力は引き続き以下とする。

- `pass`
- `warn`
- `fail`

ただし、その内訳として上記 taxonomy を report / record / support で扱う。

roll-up の原則は以下とする。

- `PASS` -> gate 上の pass 候補
- `WARN` -> gate 上の warn 候補
- `QUALITY_FAIL` -> gate 上の fail 候補
- `INFRA_ERROR` -> gate 上の fail 候補
- `CONFIG_ERROR` -> gate 上の fail 候補
- `REVIEW_REQUIRED` -> active gate の分母には入れない
- `SKIPPED` -> active gate の分母には入れない

### 3. 品質問題と接続問題を明確に分ける

以下は品質問題として扱う。

- retrieval miss
- keyword miss
- bad reference
- judge relevance 低下
- faithfulness 低下
- evidence recall 低下

以下は接続問題として扱う。

- external timeout
- auth error
- external 5xx
- adapter unavailability
- transient network failure

この分離は gate の見た目だけでなく、 failure review と support routing でも維持する。

### 4. `WARN` は品質懸念だが即 block しない

`WARN` は以下のような状態を含む。

- gate しきい値には届いているが、 watch したい quality drift
- report 上の judge relevance warning
- 直ちにケース無効化すべきではないが、継続観察すべき兆候

`WARN` はデフォルトでは block しない。ただし CI や環境ごとの運用で `warn` を block したい場合は既存の `warn_exit_code` 等で制御する。

### 5. `REVIEW_REQUIRED` は review / governance の状態であり、品質 pass ではない

以下は `REVIEW_REQUIRED` に含める。

- `draft` や `needs_review` のケース
- mixed question を含む review row
- split candidate の未承認提案
- auto-generated `expected_answer` draft の未確定状態

`REVIEW_REQUIRED` は gate の pass に算入しない。

レビューが終わって `active` になるまでは、 quality result とは切り離して扱う。

### 6. `SKIPPED` は明示的理由つきでのみ許容する

`SKIPPED` は以下のような場合に使う。

- status が `deprecated` のため除外
- pack 絞り込みや active filter により対象外
- 実験的機能が opt-in されておらず未実行
- operator が明示的に skip した

`SKIPPED` を silent pass として扱わない。

### 7. 各状態はアクションオーナーを伴う

- `PASS`
  - action: 維持
  - owner: なし
- `WARN`
  - action: 継続監視、必要なら tuning
  - owner: pack owner / quality owner
- `QUALITY_FAIL`
  - action: retrieval, prompt, case, evidence, answer path の修正
  - owner: system owner / pack owner
- `INFRA_ERROR`
  - action: 接続・認証・可用性の修正
  - owner: integration owner / platform owner
- `CONFIG_ERROR`
  - action: schema / config / adapter mapping 修正
  - owner: integration owner / repo maintainer / pack owner
- `REVIEW_REQUIRED`
  - action: 人手レビュー、merge 判断、promotion 判断
  - owner: reviewer / pack owner
- `SKIPPED`
  - action: skip reason の妥当性確認
  - owner: operator / reviewer

## Consequences

### Good

- 品質失敗と接続失敗を同じ箱に入れずに済む
- report と support の切り分けがしやすくなる
- review.csv や auto-generated 補助値を品質 pass と混同しにくくなる
- 既存 gate の outward behavior を維持しながら内訳を豊かにできる

### Trade-offs

- 状態分類が 3 値より複雑になる
- 実装と report で mapping を維持する必要がある
- 一部の失敗は `QUALITY_FAIL` と `CONFIG_ERROR` の境界判断が必要になる

## Alternatives Considered

### 1. `pass / warn / fail` だけで運用し続ける

却下。

これでは external RAG 接続時の timeout や auth failure と品質 fail が混ざる。

### 2. infra error も quality fail に寄せる

却下。

誰が直すべきかが不明確になり、 failure review が不毛になる。

### 3. review 状態を gate 状態に含めない

却下。

現在の `review.csv`, `draft`, `needs_review`, mixed question, split candidate を説明できなくなる。

## Open Questions

- `QARunRecord` や gate report に taxonomy フィールドを追加するか
- `WARN` の標準 subreason を定義するか
- `INFRA_ERROR` が一部ケースだけに発生したときの roll-up を厳密にどうするか
- `SKIPPED` の理由コードを標準化するか
- `REVIEW_REQUIRED` を report のどのセクションに常設するか