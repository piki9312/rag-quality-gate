# RAG Quality Gate

[日本語](#日本語--japanese) | [English](#english)

## 日本語 / Japanese

RAG/Agent の品質を、毎回同じやり方で検証してリリース判定までつなぐための実運用向け品質ゲート基盤です。

この製品は AI を賢くするものではなく、AI を安全に更新・運用するための品質管理レイヤです。

最初の市場導線として、社内文書（規程・FAQ・手順書・ナレッジ記事・社内 Wiki）向け縦パックを同梱しています。

## この製品が解決すること

- 変更のたびに品質確認が属人化する
- 重大ケースの取りこぼしが発生する
- 問題が出ても、どこから直すべきか分かりにくい
- PR の品質判定基準が曖昧で意思決定が遅くなる

## 提供価値

- 回帰チェックを定型化し、判断コストを下げる
- 重要ケースを先に守る運用を定着させる
- fail 時の見直し対象を明確化する
- CI と連携して release gate を自動化する

## 最初の縦パック（社内文書向け）

このリポジトリの初期パックは、社内文書を知識源とする業務支援 AI を想定しています。

- 文書更新時に impacted cases を特定する
- 重大ケース（S1）を優先して eval/check する
- pass/warn/fail で本番反映の可否を判断する
- fail を review と改善アクションに接続する

中身は水平な品質ゲート基盤のまま維持し、縦パックは導入しやすく価値を伝えるための入口として提供します。

## 5-10分で体験する

前提:

- Python 3.11+
- pip

1. 依存関係をインストール

Bash / PowerShell 共通:

```bash
pip install -e ".[dev]"
```

2. オンボーディングデモを実行

```bash
python -m rqg.demo.onboarding_quickstart
```

3. 実行結果を確認

- demo_runs/onboarding_quickstart/<run-id>/summary.json
- demo_runs/onboarding_quickstart/<run-id>/artifacts/eval_cases_review.md
- demo_runs/onboarding_quickstart/<run-id>/artifacts/impact_review.md

## 最短導入（3ステップ）

1. テンプレートを配置

Bash (macOS/Linux):

```bash
cp templates/policy.yaml .rqg.yml
mkdir -p .github/workflows
cp templates/github/workflows/rqg-onboarding.yml .github/workflows/
cp -r templates/sample_pack packs/my_pack
```

PowerShell (Windows):

```powershell
Copy-Item templates/policy.yaml .rqg.yml
New-Item -ItemType Directory -Path .github/workflows -Force | Out-Null
Copy-Item templates/github/workflows/rqg-onboarding.yml .github/workflows/
Copy-Item templates/sample_pack packs/my_pack -Recurse
```

2. サンプル pack で評価と判定を実行

```bash
rqg ingest packs/my_pack/documents --index-dir index
rqg eval packs/my_pack/cases.csv --docs packs/my_pack/documents --mock --index-dir index --log-dir runs/quality
rqg check --log-dir runs/quality --config .rqg.yml
```

3. Gate 出力を確認

- runs/quality/gate-report.md
- runs/quality/gate-decision.json

## ドキュメント案内

README は製品概要と導入に絞っています。技術仕様・運用設計の詳細は docs を参照してください。

- docs ポータル（日英）: docs/README.md

導入とデモ:

- docs/demo/onboarding-quickstart.md
- docs/demo/fail-fix-cycle.md
- docs/demo/impact-cycle.md
- packs/hr/README.md

技術設計:

- docs/adr/0001-model-boundaries.md
- docs/adr/0002-product-charter-and-development-priorities.md

運用設計（Phase2 / Phase2.5）:

- docs/ops/phase2-migration-playbook.md
- docs/ops/phase2-kickoff-board.md
- docs/ops/phase2-weekly-metrics-register.md
- docs/ops/phase2-5-hardening-plan.md
- docs/ops/phase2-5-weekly-metrics-register.md
- docs/ops/phase2-5-investigate-response-flow.md
- docs/ops/phase2-5-case-quality-weekly-review.md
- docs/ops/phase3-internal-docs-vertical-pack.md

## ライセンス

MIT

---

## English

RAG Quality Gate is a production-oriented quality-gate foundation that lets teams validate RAG/Agent quality in a repeatable way and connect results directly to release decisions.

This product does not make models smarter. It provides a quality-management layer for safe updates and operations.

As the first market-facing entry point, this repository includes an internal-documents vertical pack (policy docs, FAQs, SOPs, knowledge pages, internal wiki style content).

## Problems It Solves

- Quality checks become inconsistent across changes and owners
- Critical cases are missed during regressions
- When failures happen, the next fix target is unclear
- PR-level quality criteria are ambiguous, slowing release decisions

## Value

- Standardizes regression checks and reduces decision overhead
- Keeps focus on high-priority cases first
- Clarifies what to review when a run fails
- Automates release gating through CI integration

## First Vertical Pack (Internal Documents)

The first pack in this repository is designed for assistant AI that relies on internal documents.

- Identify impacted cases when documents change
- Protect critical cases (S1) first during eval/check
- Decide production rollout with pass/warn/fail
- Connect failures to review and corrective actions

The product core remains horizontal. The vertical pack is an adoption and value-communication entry point.

## Try It In 5-10 Minutes

Prerequisites:

- Python 3.11+
- pip

1. Install dependencies

Common for Bash and PowerShell:

```bash
pip install -e ".[dev]"
```

2. Run the onboarding demo

```bash
python -m rqg.demo.onboarding_quickstart
```

3. Check outputs

- demo_runs/onboarding_quickstart/<run-id>/summary.json
- demo_runs/onboarding_quickstart/<run-id>/artifacts/eval_cases_review.md
- demo_runs/onboarding_quickstart/<run-id>/artifacts/impact_review.md

## Fast Setup (3 Steps)

1. Place templates

Bash (macOS/Linux):

```bash
cp templates/policy.yaml .rqg.yml
mkdir -p .github/workflows
cp templates/github/workflows/rqg-onboarding.yml .github/workflows/
cp -r templates/sample_pack packs/my_pack
```

PowerShell (Windows):

```powershell
Copy-Item templates/policy.yaml .rqg.yml
New-Item -ItemType Directory -Path .github/workflows -Force | Out-Null
Copy-Item templates/github/workflows/rqg-onboarding.yml .github/workflows/
Copy-Item templates/sample_pack packs/my_pack -Recurse
```

2. Run evaluation and gate decision with the sample pack

```bash
rqg ingest packs/my_pack/documents --index-dir index
rqg eval packs/my_pack/cases.csv --docs packs/my_pack/documents --mock --index-dir index --log-dir runs/quality
rqg check --log-dir runs/quality --config .rqg.yml
```

3. Review gate outputs

- runs/quality/gate-report.md
- runs/quality/gate-decision.json

## Documentation

This README focuses on product overview and onboarding. See docs for detailed technical and operational guidance.

- docs portal (JP/EN): docs/README.md

Getting started and demos:

- docs/demo/onboarding-quickstart.md
- docs/demo/fail-fix-cycle.md
- docs/demo/impact-cycle.md
- packs/hr/README.md

Architecture:

- docs/adr/0001-model-boundaries.md
- docs/adr/0002-product-charter-and-development-priorities.md

Operations (Phase2 / Phase2.5):

- docs/ops/phase2-migration-playbook.md
- docs/ops/phase2-kickoff-board.md
- docs/ops/phase2-weekly-metrics-register.md
- docs/ops/phase2-5-hardening-plan.md
- docs/ops/phase2-5-weekly-metrics-register.md
- docs/ops/phase2-5-investigate-response-flow.md
- docs/ops/phase2-5-case-quality-weekly-review.md
- docs/ops/phase3-internal-docs-vertical-pack.md

## License

MIT
