# ADR 0005: Quality Asset Governance

## Title

Quality Asset Governance

## Status

Proposed

## Date

2026-04-20

## Context

RQG では `cases.csv`、`review.csv`、snapshot、impact report、merge report など、複数の成果物が評価運用に関与する。

これらを単なる入出力ファイルとして扱うと、以下が起きやすい。

- source of truth が曖昧になる
- generated review をそのまま確定資産として誤用する
- mixed question や split candidate がそのまま active 化される
- `expected_answer` や `severity` の自動補助が、意図せず確定値として扱われる
- refresh, migration, merge の判断が属人化する

RQG repo ではケースを「品質資産」として扱い、 gate / eval / check の前提になる運用原則を固定する必要がある。

## Decision

### 1. `cases.csv` は governed quality asset の source of truth とする

pack 配下の `cases.csv` は、承認済みケース資産の正本とする。

これには以下が含まれる。

- `question`
- `expected_evidence`
- `expected_keywords`
- `expected_answer`（手動で確定された場合のみ）
- `severity`
- `eval_mode`
- `status`
- `notes`

`review.csv` や review markdown は、この正本を補助する派生成果物であり、 source of truth ではない。

### 2. `expected_evidence` を主、`source_doc` と `expected_answer` を補助とする

ケース資産の正本として最も重視するのは `expected_evidence` とする。

理由:

- retrieval quality と groundedness の両方に接続できる
- chunk / section / source mapping の起点になる
- external RAG 接続でも evidence 契約の中心に据えやすい

`source_doc` は reviewer aid として使う。

- merge 時の差分確認補助
- review.csv の可読性向上
- snapshot section と curated chunk のズレ把握

`expected_answer` は、手動で確定されるまでは補助値として扱う。

- auto-generated `expected_answer` は review 補助に留める
- exact 判定の自動昇格に使わない

### 3. review 出力は補助であり、確定資産ではない

`review.csv` と review markdown の役割は以下に限定する。

- reviewer が差分を速く確認する
- generated question と category の初期案を確認する
- mixed question, split candidate, source_doc, expected_answer draft を人手で選別する

この生成物を、そのまま source of truth として扱わない。

### 4. ケース status の意味を固定する

現在の運用上、ケース status は以下の意味を持つ。

- `active`
  - 承認済みで eval / check / gate の対象
- `draft`
  - 形は整っているが、まだ運用に載せない候補
- `needs_review`
  - ambiguous, incomplete, mixed, high-risk で追加判断が必要
- `deprecated`
  - 現行運用では除外済みのケース

この ADR では、運用概念として `obsolete` という語も許容する。ただし current schema 上は `deprecated` で表現する。

つまり、

- operational term: obsolete
- current file schema term: deprecated

とする。

### 5. mixed question は安全側に倒す

mixed question は、1 ケース 1 intent の原則から外れるため、自動で `active` にしない。

原則:

- mixed question は `needs_review` 相当で扱う
- merge 自動化では high-priority mixed row を保守的に扱う
- 必要なら split candidate を別案として出す

### 6. split candidate は補助案に留める

split candidate は reviewer の判断補助であり、確定ケースではない。

原則:

- original mixed question の代替案として提示する
- そのまま active 化しない
- intent, evidence, overlap を人手で確認してから採用する

### 7. severity は人手承認を残す

`severity` は運用上の重みづけと block 条件に直結するため、自動確定しない。

特に `S1` は以下の理由で人手承認に残す。

- gate の block 条件に直接効く
- customer / ops impact が大きい
- generated question の質や evidence の安定性だけでは決められない

### 8. refresh / migration / merge の原則を固定する

#### refresh

- source document の更新で意味が変わったら refresh 対象とする
- 既存ケースの question / evidence / category が維持できるかを 먼저確認する

#### migration

- evidence ID 体系が変わる場合は migration を明示的に行う
- snapshot section ID と curated chunk ID を silent overwrite しない

#### merge

- merge は asset governance の補助であり、自動確定手段ではない
- existing curated values を尊重し、最小差分で取り込む
- 重大な意味変更は新規 case か manual patch で扱う

## Consequences

### Good

- `cases.csv` と generated review の役割が明確になる
- mixed question や auto-generated answer の誤昇格を防ぎやすい
- severity と evidence の品質を人手で守れる
- refresh / migration / merge の判断が安定する

### Trade-offs

- 自動化の速度より review コストを優先することになる
- generated artifact を見てすぐ反映したくても、 manual patch が残る
- `deprecated` と `obsolete` の語を橋渡しする運用説明が必要になる

## Alternatives Considered

### 1. generated `review.csv` を source of truth にする

却下。

review 補助と governed asset の境界が壊れ、 curated case が守れない。

### 2. mixed question も有用ならそのまま active にする

却下。

評価の説明責任と remediation の粒度が悪くなる。

### 3. severity を自動推定してそのまま使う

却下。

S1/S2 の境界は技術推定だけで固定すべきではない。

## 追記: 設計資産としてのFailure Pattern

failure patternは、生成されたreview出力の前段にある管理対象の設計資産です。候補ケースがなぜ必要なのか、どの業務リスクを検査するのかを説明するために使います。

Gate実行における正本は引き続き `cases.csv` です。failure pattern自体がactiveになることはなく、生成候補をそのままactive caseに昇格してはいけません。

formal 16-column schemaを変えずに対応関係を追跡できるよう、採用されたケースでは `notes` にpattern参照を残します。

```text
pattern:FP-CANCEL-001
```

月額運用では、対応関係の両側を更新します。

- active caseが変わったら、failure pattern台帳の `linked_case_ids` を更新する
- 現行ポリシーに照らしてcaseをレビューしたら、`cases.csv` の `last_reviewed_at` を更新する

## Open Questions

- case lineage をより明示的に管理する field を追加するか
- obsolete / deprecated の用語を schema 上も揃えるか
- generated field に provenance stamp を付与するか
- stale case detection を repo 標準機能として持つか
- pack owner / reviewer owner を asset metadata として持つか
