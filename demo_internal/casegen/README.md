# Internal S1 Release Gate Demo Assets

このディレクトリは、Proof Gate が case生成ツールではなく
「S1重大誤回答を本番前に止める Release Gate」であることを
内部向けに最小構成で見せるためのデモ資産です。

## このディレクトリにあるもの

- `failure_patterns.md`: 3つのS1 risk pattern を説明する軽いメモ
- `s1_case_review.csv`: 人間がS1ケースを設計・承認したことを残す review artifact
- `cases.csv`: Gate 実行に使う正本

## 重要な原則

- 正本は `cases.csv`
- `failure_patterns.md` は説明資料であり正本ではない
- `s1_case_review.csv` は review artifact であり正本ではない
- S1 active case は人間が設計・承認する
- S1 active case を gen-cases から直接生成・active化してはいけない

## 実行手順

再現可能な runbook は次を参照してください。

- `/home/runner/work/rag-quality-gate/rag-quality-gate/docs/demo/internal-s1-case-authoring.md`
