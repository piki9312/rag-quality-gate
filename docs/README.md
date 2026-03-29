# Docs Portal

このディレクトリは、RAG Quality Gate の技術仕様と運用設計の詳細をまとめたドキュメント入口です。

製品概要と最短導入は [README.md](../README.md) を参照してください。

## 目的別に読む

初めて導入する:

- [onboarding-quickstart](demo/onboarding-quickstart.md)
- [fail-fix-cycle](demo/fail-fix-cycle.md)
- [impact-cycle](demo/impact-cycle.md)

Phase2 を運用する:

- [phase2-migration-playbook](ops/phase2-migration-playbook.md)
- [phase2-kickoff-board](ops/phase2-kickoff-board.md)
- [phase2-weekly-metrics-register](ops/phase2-weekly-metrics-register.md)

Phase2.5 を運用する:

- [phase2-5-hardening-plan](ops/phase2-5-hardening-plan.md)
- [phase2-5-ws1-baseline-sheet](ops/phase2-5-ws1-baseline-sheet.md)
- [phase2-5-ws2-failure-review-template](ops/phase2-5-ws2-failure-review-template.md)
- [phase2-5-ws3-gate-exception-approval-template](ops/phase2-5-ws3-gate-exception-approval-template.md)
- [phase2-5-weekly-metrics-register](ops/phase2-5-weekly-metrics-register.md)
- [phase2-5-investigate-response-flow](ops/phase2-5-investigate-response-flow.md)
- [phase2-5-case-quality-weekly-review](ops/phase2-5-case-quality-weekly-review.md)

設計意図を確認する:

- [ADR: model boundaries](adr/0001-model-boundaries.md)
- [ADR: product charter and priorities](adr/0002-product-charter-and-development-priorities.md)

## まず確認する順番

1. [onboarding-quickstart](demo/onboarding-quickstart.md) で 1 回通し実行
2. [phase2-migration-playbook](ops/phase2-migration-playbook.md) で運用前提を固定
3. [phase2-5-hardening-plan](ops/phase2-5-hardening-plan.md) で運用強化へ展開

## 補足

- ワークフロー定義は `.github/workflows/` を参照
- テンプレートは `templates/` を参照
- 実行サンプルは `demo_runs/` を参照

---

## English

This directory is the documentation entry point for detailed technical and operational guidance in RAG Quality Gate.

For product overview and quick onboarding, see [README.md](../README.md).

### Browse By Goal

Getting started:

- [onboarding-quickstart](demo/onboarding-quickstart.md)
- [fail-fix-cycle](demo/fail-fix-cycle.md)
- [impact-cycle](demo/impact-cycle.md)

Operating Phase2:

- [phase2-migration-playbook](ops/phase2-migration-playbook.md)
- [phase2-kickoff-board](ops/phase2-kickoff-board.md)
- [phase2-weekly-metrics-register](ops/phase2-weekly-metrics-register.md)

Operating Phase2.5:

- [phase2-5-hardening-plan](ops/phase2-5-hardening-plan.md)
- [phase2-5-ws1-baseline-sheet](ops/phase2-5-ws1-baseline-sheet.md)
- [phase2-5-ws2-failure-review-template](ops/phase2-5-ws2-failure-review-template.md)
- [phase2-5-ws3-gate-exception-approval-template](ops/phase2-5-ws3-gate-exception-approval-template.md)
- [phase2-5-weekly-metrics-register](ops/phase2-5-weekly-metrics-register.md)
- [phase2-5-investigate-response-flow](ops/phase2-5-investigate-response-flow.md)
- [phase2-5-case-quality-weekly-review](ops/phase2-5-case-quality-weekly-review.md)

Architecture rationale:

- [ADR: model boundaries](adr/0001-model-boundaries.md)
- [ADR: product charter and priorities](adr/0002-product-charter-and-development-priorities.md)

### Suggested Reading Order

1. Run [onboarding-quickstart](demo/onboarding-quickstart.md) once end-to-end
2. Fix operational assumptions with [phase2-migration-playbook](ops/phase2-migration-playbook.md)
3. Expand hardening with [phase2-5-hardening-plan](ops/phase2-5-hardening-plan.md)

### Notes

- See `.github/workflows/` for workflow definitions
- See `templates/` for onboarding templates
- See `demo_runs/` for execution samples