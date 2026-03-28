# RAG Quality Gate

[日本語](#日本語--japanese) | [English](#english)

## 日本語 / Japanese

RAG/Agent の品質を、毎回同じやり方で検証してリリース判定までつなぐための実運用向けツールです。

文書更新やプロンプト変更のたびに「今回は本当に安全か」を迷わず判断できる状態を作ります。

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

技術設計:

- docs/adr/0001-model-boundaries.md

運用設計（Phase2 / Phase2.5）:

- docs/ops/phase2-migration-playbook.md
- docs/ops/phase2-kickoff-board.md
- docs/ops/phase2-weekly-metrics-register.md
- docs/ops/phase2-5-hardening-plan.md
- docs/ops/phase2-5-weekly-metrics-register.md
- docs/ops/phase2-5-investigate-response-flow.md
- docs/ops/phase2-5-case-quality-weekly-review.md

## ライセンス

MIT

---

## English

RAG Quality Gate is a production-oriented toolkit that lets you validate RAG/Agent quality in a repeatable way and connect results directly to release decisions.

It helps teams answer "Is this release safe?" every time documents, retrieval settings, or prompts change.

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

Architecture:

- docs/adr/0001-model-boundaries.md

Operations (Phase2 / Phase2.5):

- docs/ops/phase2-migration-playbook.md
- docs/ops/phase2-kickoff-board.md
- docs/ops/phase2-weekly-metrics-register.md
- docs/ops/phase2-5-hardening-plan.md
- docs/ops/phase2-5-weekly-metrics-register.md
- docs/ops/phase2-5-investigate-response-flow.md
- docs/ops/phase2-5-case-quality-weekly-review.md

## License

MIT
