# ADR 0006: Responsibility Boundary For External Systems

## Title

Responsibility Boundary For External Systems

## Status

Proposed

## Date

2026-04-20

## Context

RQG が external RAG の上で使われるようになると、 failure review や support で次の論点が頻発する。

- この失敗は RQG の問題か、外部 RAG の問題か
- customer environment の設定不整合か、 repo 側の契約不整合か
- report でどう書けば「誰が何を直すか」が伝わるか

責任分界が曖昧だと、品質失敗・接続失敗・設定失敗がすべて「RAG が悪い」「RQG が悪い」に丸められてしまう。

RQG repo では blame allocation ではなく remediation boundary を固定する必要がある。

## Decision

### 1. RQG が責任を持つ範囲を固定する

RQG が責任を持つのは以下とする。

- 評価実行 (`eval`)
- 閾値判定 (`check`)
- gate 判定と report 出力 (`gate`)
- ケース資産の governance (`cases.csv`, `review.csv`, merge, validate)
- external response の正規化と adapter 境界
- エラー分類と failure category の整理
- support / review 時に使える説明可能な output の提供

RQG は「外部システムの品質を可視化し、判定し、改善に繋げる層」であり、外部システムそのものを運用・保証する層ではない。

### 2. 外部 RAG / customer environment が責任を持つ範囲を固定する

外部 RAG または customer environment が責任を持つのは以下とする。

- retrieval quality
- index freshness
- chunking quality
- metadata stability
- auth / permission / token validity
- endpoint availability
- external timeout / 5xx / rate limiting
- upstream model / retriever configuration

RQG はこれらを観測・分類・報告できるが、直接修正責任は持たない。

### 3. 共同責任の領域を明示する

以下は共同責任とする。

- adapter 契約整形
- `expected_evidence` と外部 `chunk_id` の対応づけ
- document update と snapshot 同期
- evidence ID migration
- source system change 時の pack refresh

これらは一方の責任に閉じず、 integration owner と pack owner の協調を前提とする。

### 4. 品質失敗と接続失敗を report 上でも分ける

report と support では、少なくとも以下を分離して表現する。

- quality failure
  - retrieval miss
  - bad reference
  - judge relevance / faithfulness 低下
- infra failure
  - timeout
  - auth failure
  - 5xx
  - adapter unavailability
- config failure
  - schema mismatch
  - required field missing
  - invalid integration config

この分離は、「誰のせいか」ではなく「次に誰が直すか」を明確にするために行う。

### 5. support の標準表現は blame ではなく remediation で書く

support や report の文言は以下の方針に従う。

- 悪い例
  - 外部 RAG が壊れている
  - customer 側の問題
- 良い例
  - external retrieval endpoint returned timeout; integration owner should verify endpoint health and retry policy
  - expected evidence no longer matches current chunk IDs; pack owner and integration owner should refresh mapping
  - answer quality failed against current retrieved context; system owner should inspect retrieval / prompting behavior

### 6. 代表的な failure の責任境界を固定する

- external timeout / auth / 5xx
  - primary owner: external system owner / platform owner
  - RQG responsibility: classify as infra, surface in report
- retrieval miss with valid contract and stable evidence mapping
  - primary owner: system owner
  - RQG responsibility: measure and report
- missing `chunk_id` / missing `text` / invalid payload shape
  - primary owner: integration owner
  - RQG responsibility: reject as config error
- stale `expected_evidence` after index rebuild or chunking change
  - joint owner: pack owner + external system owner
  - RQG responsibility: expose mismatch and preserve audit trail

## Consequences

### Good

- report と support で揉めにくくなる
- RQG の責務が「評価・可視化・判定」であることを保てる
- external RAG integration の triage がしやすくなる
- pack owner と integration owner の共同作業点が明示される

### Trade-offs

- 一部の事象は境界が完全にきれいに分かれない
- report にオーナー視点を持ち込むための整理コストが増える
- 「観測はするが修正責任は持たない」領域の説明が必要になる

## Alternatives Considered

### 1. RQG が end-to-end 品質に全面責任を持つ

却下。

外部 RAG の可用性や auth まで repo の責務にすると、責任範囲が過大になる。

### 2. customer environment 側の責任にすべて寄せる

却下。

adapter 正規化や error classification まで external 側任せにすると、 RQG の存在意義が弱くなる。

### 3. 責任境界を文書化せず case-by-case で判断する

却下。

support と review の一貫性が保てない。

## Open Questions

- report に owner hint を機械可読で持たせるか
- support 向け標準テンプレートを repo に置くか
- external SLA / timeout budget を repo 設定として持つか
- joint responsibility issue の escalation ルールをどこに置くか
- adapter health check を標準化するか