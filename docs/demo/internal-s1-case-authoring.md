# Internal S1 Case Authoring Demo

## このデモの目的

このデモの目的は、Proof Gate が単なる case 生成補助ではなく、
S1重大誤回答を本番前に止める Release Gate であることを
内部向けに最小構成で再現することです。

このデモでは、返金・解約・個人情報開示の3件だけを扱います。
重点は failure pattern の資産化ではなく、
人間が承認した S1 active case が `cases.csv` に入り、
`rqg gate --mock` で BLOCK を確認できることです。

## S1 / S2 の違い

- `S1`: 業務事故を止めるために、人間が設計・承認する Safety Gate ケース
- `S2`: 文書網羅や説明品質を見るための Quality Gate ケース

S1 は少数でよく、生成よりも承認品質が重要です。
S2 は広い回帰確認を支えるために生成支援を使えます。

## failure pattern の位置づけ

`demo_internal/casegen/failure_patterns.md` は、なぜ S1 ケースが必要かを説明する
内部メモです。正本ではありません。parser も実装しません。

この段階での failure pattern は、
S1 ケースを作りやすくする補助線に留めます。

## 正本は cases.csv

このデモにおける Gate 実行の正本は次です。

- `/home/runner/work/rag-quality-gate/rag-quality-gate/demo_internal/casegen/cases.csv`

`s1_case_review.csv` は承認の痕跡であり、
`failure_patterns.md` は設計メモです。
どちらも Gate 実行の正本ではありません。

## S1 case 作成フロー

1. サンプルポリシー文書を作る
2. failure pattern を3件だけ整理する
3. 人間が `s1_case_review.csv` で actual case を設計・承認する
4. 承認済みの S1 case だけを `cases.csv` に反映する
5. `manual_review_required` / `pattern:FP-...` / `block_reason:...` を `notes` に残す
6. `validate-pack --strict-s1-governance` で S1 governance を確認する
7. `rqg gate --mock` で BLOCK を確認する

## mock での BLOCK 確認手順

### 1. validate-pack

```bash
cd /home/runner/work/rag-quality-gate/rag-quality-gate
python3 -m rqg.cli validate-pack \
  --pack-dir /home/runner/work/rag-quality-gate/rag-quality-gate/demo_internal \
  --strict-s1-governance
```

期待結果:

- `Pack onboarding validation: OK`
- S1 active case の governance 必須項目が満たされる

### 2. gate --mock

`--mock` は内部デモ専用です。顧客向け品質証跡ではありません。

```bash
cd /home/runner/work/rag-quality-gate/rag-quality-gate
export EMB_MODEL=local-fallback-hash-embedding
python3 -m rqg.cli gate \
  /home/runner/work/rag-quality-gate/rag-quality-gate/demo_internal/casegen/cases.csv \
  --docs /home/runner/work/rag-quality-gate/rag-quality-gate/demo_internal/documents \
  --quality-pack /home/runner/work/rag-quality-gate/rag-quality-gate/demo_internal/quality-pack.yml \
  --config /home/runner/work/rag-quality-gate/rag-quality-gate/demo_internal/gate.yml \
  --mock \
  --strict-s1-governance \
  --reset-log-dir \
  --index-dir /tmp/rqg-internal-s1-demo-index \
  --log-dir /tmp/rqg-internal-s1-demo-logs
```

期待結果:

- `Gate: FAIL`
- `Policy: BLOCK`
- `gate-report.md` の S1重大失敗一覧で止まった理由が読める
- `gate-decision.json` の `policy_status` が `block` になる

このデモの mock run では、文書根拠が存在していても
承認済み S1 expected answer を満たさない回答を BLOCK できることを確認します。

## SIMULATION ONLY

`rqg gate --mock` の結果は **SIMULATION ONLY** です。

- 内部デモ用の挙動確認には使える
- 顧客品質証跡には使えない
- 有償PoCや customer-facing report の正式証跡には real / external_real run が必要

## 資産化は PoC 2〜3回後でよい

この段階では、failure pattern の registry 化や usage log は不要です。
まずは、少数の人間承認 S1 case で Release Gate を成立させることを優先します。

PoC を 2〜3 回回して、どの pattern が再利用されるかが見えてから、
資産化を検討すれば十分です。

## やらないこと

このデモでは次をやりません。

- asset registry
- usage log
- seen_count
- failure_patterns.csv 化
- failure_patterns.md parser 実装
- `gen-cases --failure-patterns`
- `cases.csv` schema 変更
- GateDecision / report schema 変更
- workflow 変更
- common pack 分割
- customer-specific pattern pack 分割
- S1 active case の自動生成
- 顧客に `cases.csv` を直接編集させる前提の運用
