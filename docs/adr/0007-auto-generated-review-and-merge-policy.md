# ADR 0007: Auto-generated Review And Merge Policy

## Title

Auto-generated Review And Merge Policy

## Status

Proposed

## Date

2026-04-20

## Context

RQG は `gen-cases`, `review.csv`, review markdown, `merge-cases`, source_doc 補完, mixed question 検出, split candidate 生成などを持つ。

これらは reviewer の負荷を大きく下げる一方で、 asset governance の境界が曖昧になると以下の危険がある。

- generated review をそのまま source of truth として取り込む
- curated な `expected_keywords`, `expected_evidence`, `severity` が上書きされる
- mixed question の original row が毎回戻ってくる
- auto-generated `expected_answer` が exact 判定へ誤昇格する
- merge の便利さが資産保全を上回る

この ADR は、自動補助をどこまで許し、どこから人手確認を必須にするかを固定する。

## Decision

### 1. generated review は人手確認の補助出力とする

`review.csv` と review markdown は、 reviewer が差分確認・分類・選別を速く行うための補助出力とする。

以下の用途を想定する。

- generated question の一次確認
- `source_doc` や `category` の初期補助
- mixed question / split candidate の発見
- `expected_answer` draft の目視確認

この出力を、そのまま source of truth にしない。

### 2. merge-cases は保守的に動く

`merge-cases` は便利機能ではあるが、目的は「運用資産を守りながら取り込みを楽にすること」である。

原則:

- blind overwrite しない
- curated row の意味変更を自動で確定しない
- 最小差分で取り込む
- ambiguous row は skip または review 側に倒す

### 3. curated 値を優先する

既存 `cases.csv` に人手で調整された値がある場合、 generated 値より curated 値を優先する。

特に保護対象とする項目:

- `expected_keywords`
- `expected_evidence`
- `severity`
- `eval_mode`
- `notes` の人手判断部分

比較的 backfill を許容しやすい項目:

- `source_doc`
- ordinal cleanup 後の question signature 補助
- category の初期案

### 4. `expected_answer` 自動生成は draft 補助に留める

auto-generated `expected_answer` は、人手レビューを速くするための下書きとする。

許容すること:

- review.csv への出力
- notes で provenance を明示する
- extract-only の安全な補助
- opt-in の LLM draft

許容しないこと:

- 自動で `exact` へ昇格させる
- human review なしで `active` にする
- curated `expected_answer` を無条件で置き換える

### 5. severity 自動確定は行わない

generator や merge は severity を確定しない。

理由:

- `S1` は gate block 条件に直結する
- case importance は retrieval / wording だけでは決められない
- support / ops / compliance 観点が必要になる

### 6. mixed question は便利さより安全を優先する

mixed question original は、 automation で無理に取り込まない。

原則:

- mixed + high priority row は skip を優先する
- split candidate は reviewer 向けの代替案に留める
- original を残す場合も review required とする

### 7. index / evidence 体系が異なる場合は manual alignment を優先する

generated review が snapshot section ID を持ち、 curated active case が stable chunk ID を持つような場合、 merge は慎重に扱う。

この場合の原則:

- taxonomy alignment や manual patch を優先する
- blind に evidence を置き換えない
- lineage を失う自動上書きはしない

## Consequences

### Good

- generated review の便利さを活かしつつ、 curated asset を守れる
- `expected_answer` の誤昇格を防ぎやすい
- mixed question や split candidate を安全側で扱える
- merge の結果が reviewer に説明しやすくなる

### Trade-offs

- 手作業の patch や taxonomy alignment が残る
- aggressive automation より運用速度は落ちる
- generated output を全面採用したい場面でも抑制がかかる

## Alternatives Considered

### 1. generated review をそのまま in-place merge する

却下。

資産保全より convenience が勝ってしまう。

### 2. merge を一切持たず、すべて手動で反映する

見送り。

安全だが、 reviewer の負荷が高すぎる。

### 3. auto-generated `expected_answer` を exact 判定へ自動採用する

却下。

評価契約が壊れ、 review 補助と正本の境界が失われる。

## 追記: Failure Patternとの追跡性

生成されたreview出力は、引き続き候補artifactです。`cases.csv` に昇格する前に、failure patternと照らしてレビューします。

failure patternは、そのcaseがなぜ存在するのか、AI/RAGが起こしてはいけない業務事故は何かを説明します。運用上の正本は `cases.csv` のままですが、採用された行では `notes` に軽い参照を残します。

```text
pattern:FP-REFUND-001
```

この参照は、新しいformal columnを増やさず、意図的に `notes` に保存します。既存の16列schemaを維持しながら、PoCレビューと月額運用で追跡できるようにするためです。

validatorは、次の場合にerrorではなくwarningを出します。

- activeな `S1` caseに `pattern:` 参照がない
- `pattern:` 参照が `pattern:FP-[A-Z0-9-]+` に一致しない

validatorは `failure_patterns.md` をパースせず、pattern IDの存在確認もしません。存在確認は、failure pattern台帳の形式が安定した後に検討します。

## Open Questions

- curated field lock を file schema 上に持つか
- merge report に provenance をどこまで出すか
- reviewer approval manifest を追加するか
- generated `expected_keywords` の trust level を field 単位で持つか
- split candidate 採用時の lineage 記録を標準化するか
