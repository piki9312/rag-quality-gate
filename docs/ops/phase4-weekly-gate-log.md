# Phase 4 Weekly Dog-fooding Gate Log

週次ゲート実行の 4 週間追跡テンプレート。  
GitHub Actions の `phase4-weekly-gate.yml` が毎週月曜に自動実行し、
結果を Issue に投稿します。このファイルには確認済み週のサマリを手動で記入してください。

## 追跡対象

- **Pack**: `packs/hr` (HR/Policy プロファイル, 17 ケース: S1=7 / S2=10)
- **SLO**: `s1_pass_rate=1.00`, `overall_pass_rate=0.85`
- **LLM モード**: mock (CI), real (手動 `workflow_dispatch` + `OPENAI_API_KEY` secret)

---

## 4 週間運用記録

| Week | 日付 | Gate Status | Overall Pass Rate | S1 Pass Rate | 備考 / Issue |
|------|------|-------------|-------------------|--------------|--------------|
| W1   | -    | -           | -                 | -            | -            |
| W2   | -    | -           | -                 | -            | -            |
| W3   | -    | -           | -                 | -            | -            |
| W4   | -    | -           | -                 | -            | -            |

> **記入方法**: 上の表を毎週更新してください。Gate Status は `✅ pass` または `❌ fail`。
> Issue 欄には `[#NNN](URL)` 形式でリンクを貼ってください。

---

## 4 週間完走チェック (E1-E4)

Phase 2.5 の hardening 基準に準じた dog-fooding 完走条件です。

| 条件 | 内容 | 達成状況 |
|------|------|----------|
| E1 | 4 週連続で gate が自動実行された | - |
| E2 | 全 S1 ケースで s1_pass_rate=1.00 を維持 | - |
| E3 | fail 発生時に原因特定 → 再 pass まで追跡した | - |
| E4 | `packs/hr/quality-pack.yml` の roi 数値が実測値に更新された | - |

---

## dog-fooding で発見した改善点

> 実運用中に見つかった問題・改善案を下に記録してください。

<!-- 例:
- 2026-05-01: HR004 が retrieval_miss で繰り返し fail。chunking パラメータを調整（PR #xxx）。
- 2026-05-08: LLM judge fallback が 3/17 ケースで発生。API タイムアウト設定を見直し。
-->

---

## ワークフロー手動実行手順

```bash
# GitHub CLI で手動実行 (mock モード)
gh workflow run phase4-weekly-gate.yml

# Real LLM モードで実行 (OPENAI_API_KEY secret が設定済みの場合)
gh workflow run phase4-weekly-gate.yml -f use_real_llm=true

# 特定 pack を指定
gh workflow run phase4-weekly-gate.yml -f pack=packs/hr -f use_real_llm=false
```

## 関連ドキュメント

- [`.github/workflows/phase4-weekly-gate.yml`](../../.github/workflows/phase4-weekly-gate.yml)
- [`packs/hr/quality-pack.yml`](../../packs/hr/quality-pack.yml) — ROI セクション参照
- [`packs/hr/gate.yml`](../../packs/hr/gate.yml) — SLO 設定
- [`docs/ops/phase2-5-weekly-metrics-register.md`](phase2-5-weekly-metrics-register.md) — Phase 2.5 週次記録同形式
