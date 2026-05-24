# ケース下書きレビュー導線

## 概要

Proof Gate は、顧客固有の正式な `expected_answer` を自動確定しません。
`gen-cases` や draft case generation はカバーすべき観点を提案しますが、
生成された case はまず `status=needs_review` の下書きとして扱います。

ベンダーは `review_cases.yaml` を確認・編集し、`decision: approve` とした
case だけを `approve-cases` で `status=active` に変換します。Gate は既存通り
`active` case だけを実行対象にします。

## 基本フロー

1. `cases_draft.csv` を生成または準備します。
2. draft row は必ず `status=needs_review` にします。
3. レビュー用 artifact を出力します。

   ```bash
   rqg export-case-review \
     --draft cases_draft.csv \
     --output-yaml review_cases.yaml \
     --output-md review_cases.md
   ```

4. ベンダーは `review_cases.yaml` を編集します。
5. `review_cases.md` は人間向け preview です。機械読み取りの正本は
   `review_cases.yaml` です。
6. 承認済みレビュー結果を `cases.csv` に反映します。

   ```bash
   rqg approve-cases \
     --draft cases_draft.csv \
     --review review_cases.yaml \
     --output cases.csv
   ```

7. `decision: approve` の row だけが `status=active` になります。

## レビュー判断

| `decision` | 出力 status | Gate 実行対象 |
| --- | --- | --- |
| `pending` | `needs_review` | 対象外 |
| `approve` | `active` | 対象 |
| `reject` | `deprecated` | 対象外 |

`reject` は出力から削除せず、`deprecated` として残します。これにより、
レビュー履歴を追跡でき、かつ Gate 実行対象からは外せます。

## YAML はベンダー所有 artifact

`review_cases.yaml` には、顧客固有の期待回答や根拠情報が入る可能性があります。
これは vendor-owned / internal artifact として扱ってください。
GitHub-hosted CI へ upload する場合は、その boundary に出してよいデータであることを
事前に確認してください。

## 最小スキーマ

YAML キーは機械読み取りの正本なので英語のまま固定します。

```yaml
version: 1
generated_by: proof_gate_review_flow
cases:
  - case_id: draft_hr_deadline_001
    decision: pending
    status: needs_review
    suggestion:
      name: Leave request deadline review
      question: When must paid leave be requested?
      intent: deadline_check
      failure_pattern: deadline_or_period_mismatch
      severity_hint: S1
      evidence_requirement:
        - deadline
      expected_behavior_template:
        - cite_expected_evidence
    vendor_review:
      expected_answer: ""
      expected_evidence: []
      expected_keywords: []
      severity: S1
      eval_mode: evidence_keyword
      reviewed_by: ""
      reviewed_at: ""
      notes: ""
```

`approve-cases` は `vendor_review.expected_answer`, `expected_evidence`,
`expected_keywords`, `severity`, `eval_mode`, `reviewed_by`, `reviewed_at` を
生成後の `cases.csv` に反映します。

## Markdown preview の位置づけ

`review_cases.md` はレビューしやすくするための補助資料です。表示ラベルは日本語ですが、
`expected_answer` や `decision` などのキー名・値は YAML と同じ英語表記を維持します。
Markdown を編集しても `approve-cases` には反映されません。
