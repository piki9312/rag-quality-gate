# Quality Pack Spec

## 定義

Quality Pack とは、**特定業務領域に対する failure patterns、test cases、Gate Policy、report template をまとめた再利用可能パッケージ** である。

目的は、案件ごとにゼロから評価設計をやり直さず、業務別の高リスク観点と Release Decision を再利用できるようにすること。

## 推奨ディレクトリ構成

```text
packs/
  customer_support/
    pack.yml
    cases_template.csv
    failure_patterns.yml
    risk_categories.yml
    gate_policy.yml
    report_template.md
    CHANGELOG.md
```

> Note: 現在の runnable pack では `quality-pack.yml` や `gate.yml` を使う箇所がある。既存契約を壊さないことを優先し、`pack.yml` / `gate_policy.yml` を導入する場合は対応関係を README や CHANGELOG に明記する。

## 各ファイルの役割

- `pack.yml`: pack の識別情報、対象業務、対応リスク領域、更新日を持つ manifest
- `cases_template.csv`: 新規案件へ展開するためのケース雛形
- `failure_patterns.yml`: 典型的な失敗パターンと観測ポイント
- `risk_categories.yml`: 業務リスク分類と severity 判断補助
- `gate_policy.yml`: BLOCK / REVIEW / PASS を決める判定ルール
- `report_template.md`: 顧客提出レポートや内部報告の標準骨子
- `CHANGELOG.md`: いつ・誰が・なぜ・何を変えたかの履歴

## `pack.yml` に含めるべき項目

```yaml
pack_id:
version:
domain:
description:
updated_at:
supported_risk_areas:
```

補足:

- `pack_id`: stable ID を使う
- `version`: pack の配布・報告に使う
- `domain`: 例 `customer_support`, `hr_policy`, `internal_rules`
- `supported_risk_areas`: 返金、解約、期限、資格条件などの対象範囲

## `cases_template.csv` に含めるべき項目例

```text
case_id
name
severity
risk_area
input
expected_behavior
forbidden_behavior
required_evidence
tags
```

補足:

- `case_id` は stable ID を使う
- `severity` は S1 / S2 を明示する
- `risk_area` は pack 内の分類と揃える
- `forbidden_behavior` は BLOCK 条件の説明責任に効く
- `required_evidence` は groundedness と review の起点にする

## `gate_policy.yml` に含めるべきルール例

```yaml
rules:
  - condition: S1 fail
    action: BLOCK
  - condition: S2 threshold fail
    action: REVIEW
  - condition: forbidden_behavior detected
    action: BLOCK
  - condition: missing evidence for S1
    action: BLOCK
```

## Quality Pack 設計原則

- 業務別 failure patterns を中心に作る
- 顧客固有ケースは、そのまま shared pack へ戻さない
- demo data と shared templates だけを repo に置く
- report template は顧客説明と machine-readable decision の両方を意識する
- pack 単位で version と changelog を必ず持つ
