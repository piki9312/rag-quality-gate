# Internal Case Generation Demo

## Purpose

この内部デモは、Proof Gate のテストケース作成フローを確認するためのものです。

Proof Gate のケース作成は、単なる QA 自動生成ではありません。AI/RAG がどのように間違えると業務事故になるかを failure pattern として整理し、それを検査する候補ケースを作り、人間レビューを通して S1/S2 ケースに承認します。

## Flow

1. `customer_support_policy.md` を確認する
2. risk area を洗い出す
3. `failure_patterns.md` を作成する
4. `gen-cases` で `eval_cases_review.csv` を生成する
5. `eval_cases_review.csv` を人間が確認する
6. failure pattern と照らして S1 / S2 / REVIEW / REJECT に分類する
7. `merge-cases` で既存 `cases.csv` に取り込む
8. `validate-cases` で検証する
9. active `cases.csv` を Gate 実行に使う

```text
document snapshot
  -> failure_patterns.md
  -> gen-cases
  -> eval_cases_review.csv
  -> human review
  -> merge-cases
  -> validate-cases
  -> cases.csv
```

## Important Principle

- `gen-cases` の出力は正本ではない
- `gen-cases` は S1 を自動決定しない
- `gen-cases` の出力は `needs_review` として扱う
- S1 は人間が承認する
- S1 には `expected_answer`, `expected_evidence`, `block_reason` が必要
- 正本は human review / merge / validate を通過した `cases.csv`

## Relationship

| Asset | Meaning |
|---|---|
| failure pattern | AI がどう間違えると危険か |
| generated candidate case | failure pattern や文書根拠から作られた検査候補 |
| active case | 人間レビューを通過し、Gate で使う承認済みケース |
| `cases.csv` | Gate で使う正本 |

Failure pattern は `cases.csv` の前段にあるリスク設計資産です。生成候補は failure pattern に照らしてレビューし、業務事故につながる誤回答を S1/S2 として承認します。

## Demo Commands

```powershell
# 1. generated candidates を確認
notepad demo_internal\casegen\eval_cases_review.csv

# 2. 既存cases.csvにマージ
.\.venv\Scripts\python -m rqg.cli merge-cases `
  --cases templates\sample_pack\cases.csv `
  --review demo_internal\casegen\eval_cases_review.csv `
  --output demo_internal\casegen\merged_cases.csv `
  --report demo_internal\casegen\merge_report.json

# 3. マージ結果を検証
.\.venv\Scripts\python -m rqg.cli validate-cases `
  --cases demo_internal\casegen\merged_cases.csv

# 4. merge report確認
.\.venv\Scripts\python -m json.tool demo_internal\casegen\merge_report.json
```

## Review Checklist

- Candidate case がどの failure pattern を検査しているか分かる
- S1/S2 にする理由が業務リスクとして説明できる
- S1 には `expected_answer`, `expected_evidence`, `block_reason` が入っている
- `source_refs` が policy snapshot の根拠セクションに対応している
- 単なるFAQ確認、表現ゆれ、低リスクの説明不足を S1 active にしていない

## Non-goals

- `gen-cases` CLI の大幅変更
- `gen-cases` 出力の自動 S1 active 化
- 顧客固有データ、API キー、実 endpoint の追加
- 正本 `cases.csv` スキーマの変更
