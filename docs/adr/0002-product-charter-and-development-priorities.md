# ADR 0002: Product Charter And Development Priorities

## Status

Accepted

## Context

Phase 1 から Phase 2.5 までで、品質ゲート基盤の骨格は成立した。

- ingest -> snapshot -> eval -> check の最小ループ
- impact / review / migrate-cases による変更運用
- Phase2 の移行 playbook と週次計測
- Phase2.5 の WS1/WS2/WS3 と M1-M5 自動化

一方で、機能増加により「何を優先し、何を後回しにするか」の判断が分散しやすくなった。
今後の実装をぶらさないため、プロダクト憲章と開発優先順位を ADR として固定する。

## Product Definition (Fixed)

このプロダクトは AI を賢くするものではない。

目的は、RAG/Agent を安全に更新・運用できる品質管理レイヤを提供することである。

対象:

- 文書更新
- モデル変更
- プロンプト変更
- retrieval 変更
- ツール変更

期待する結果:

- 品質劣化を検知できる
- 変更前後を比較できる
- 重大ケースを守れる
- fail を改善アクションにつなげられる
- リリース判定を運用可能な形で残せる

## Current Product Position

現在地は「Phase 2 完了直前から Phase 2.5 初期」である。

成立済み:

- 品質ゲート最小ループ
- 変更影響分析とレビュー導線
- legacy 互換の移行運用と撤去準備
- 週次メトリクス運用と hardening 基盤

未完了:

- 連続週の実運用証跡蓄積
- 組織運用としての習慣化強化

## Decision

### 1. Center Value

価値の中心は「回答品質そのもの」ではなく「安全な更新と運用」である。

### 2. Current Scope

現時点の製品スコープは以下に固定する。

- 社内文書など文書知識源を使う RAG/Agent の変更品質を守るゲート
- 文書差分に強い品質ゲートを最初の製品として成立させる

将来の拡張余地（構造化データ、API 出力、ツール実行）は認めるが、現行フェーズの主戦場にしない。

### 3. Priority Order For Implementation

実装判断は以下の優先順位で行う。

1. 品質ゲートとしての核を壊さない
2. 導入障壁を下げる
3. 実運用で嫌われない
4. fail から改善につながるループを強化する
5. Pack 化 / 有償 PoC / 将来 SaaS 化へ整理する

### 4. Explicitly Deprioritized (Now)

現時点では以下を優先しない。

- AI アプリ本体の機能拡張
- 過剰な UI 化
- 早すぎる SaaS インフラ実装
- 入力媒体の過度な一般化
- 本質価値に直結しない機能追加

### 5. Legacy Compatibility Policy

legacy 互換は恒久化しない。

- legacy expected_evidence 救済は期間限定移行策とする
- strict-only を最終運用形とする
- 互換に関する新規実装は「撤去可能性」を必須条件とする

### 6. Engineering Principles

機能追加より、以下を優先する。

- 運用再現性
- 可視化
- 改善ループ接続
- 撤去可能性

### 7. Documentation Ownership (Where To Write What)

| Document | Purpose | What to write |
| --- | --- | --- |
| README.md | 製品と導入の入口 | 価値、対象課題、最短導入、導線のみ |
| docs/README.md | 文書全体のナビゲーション | 目的別導線、読む順番 |
| docs/adr/*.md | 変更しにくい設計原則 | 境界、優先順位、非優先、恒久方針 |
| docs/ops/*playbook*.md | フェーズ運用ルール | 開始条件、ロールバック、週次手順 |
| docs/ops/*template*.md | 実行フォーマット | 週次レビュー、KPI、PR/issue で使う定型文 |

## Review Criteria For Code Changes

コード変更時は、次を満たすことをレビュー条件とする。

1. 変更が品質ゲートの核（ingest/snapshot/eval/check/impact）を壊していない
2. 変更理由が「安全な更新・運用」に接続されている
3. fail 時の改善導線（owner / due / next action）が定義されている
4. 例外運用を追加する場合、期限・承認・監査項目がある
5. レガシー救済を増やす場合、撤去条件と期限が明記されている
6. docs と workflow の運用導線が同時に更新されている

## Short Decision Text For Issues/PRs

Issue/PR で使う短文基準:

- This change improves safe update/operation of the quality gate, not model intelligence itself.
- Scope stays in document-diff quality gate; no broad input-media generalization in this phase.
- Priority order: core safety -> onboarding friction -> operational acceptability -> fail-to-fix loop.
- Legacy compatibility remains temporary and removable.

## Direction

### Near-term

- failure category ごとの推奨アクション定義強化
- investigate 標準対応フロー定着
- override / warn-only / no-data 厳格運用
- case 品質レビュー定例化
- onboarding / weekly ops 実測蓄積

### Mid-term

- 通しデモ固定
- sample pack 1-2個整備
- 非技術者向け週次レポート整備
- fail 時修正導線の一枚化
- 有償 PoC 向けパッケージ化

### Long-term

- SaaS 化
- Web UI
- テナント分離
- 認証 / 認可
- 実行履歴 DB
- 通知連携

## Consequences

Good:

- 実装判断が「何を作るか / 何を今は作らないか」で揃う
- docs / ops / CI の更新方針が一貫する
- エージェント・開発者のレビュー観点が共有される

Trade-off:

- スコープを意図的に絞るため、短期的には要望を断る判断が増える

ただし、文書差分品質ゲートとして一度成立させることを優先し、この制約を受け入れる。