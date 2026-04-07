# Phase2.5 と Phase3 の差分表（1ページ）

このページは、Phase2.5 から Phase3 への変更点を「新規」と「据え置き」に分けて 1 枚で把握するための運用メモです。

対象:

- Phase2.5: 実運用ハードニング（週次運用、exit/risk control）
- Phase3: 社内文書向け縦パックの製品化（導入導線と契約面の固定）

## 差分サマリ

| 項目 | Phase2.5 | Phase3 | 判定 | 根拠 |
|---|---|---|---|---|
| フェーズ主目的 | 運用で壊れにくくする（WS1/WS2/WS3、C1-C4、RC1-RC2） | 社内文書向け縦パックを実装基準付きで固定 | 新規（目的追加） | docs/ops/phase2-5-hardening-plan.md, docs/ops/phase3-internal-docs-vertical-pack.md |
| 共通基盤（ingest/eval/check/impact/review/CI） | 基盤として運用強化の対象 | 「中身は水平」の前提を維持 | 据え置き | docs/ops/phase3-internal-docs-vertical-pack.md |
| 週次運用コントロール | C1-C4, RC1-RC2 を運用・自動判定 | 同コントロールを継承して縦パック運用へ接続 | 据え置き（継承） | docs/ops/phase2-5-hardening-plan.md, docs/ops/phase3-internal-docs-vertical-pack.md |
| 縦パック最小構成の固定 | 明確な固定定義は未中心 | documents/cases/gate/quality-pack/README を必須化 | 新規 | docs/ops/phase3-internal-docs-vertical-pack.md |
| Pack責務と基盤責務の境界 | 運用上は存在 | Phase3で原則として明文化・固定 | 拡張（明文化） | docs/ops/phase3-internal-docs-vertical-pack.md, docs/adr/0001-model-boundaries.md |
| 製品メッセージ | 運用ハードニング中心 | 社内文書向け縦プロファイル（HR + Wiki/FAQ）を前面化 | 拡張 | README.md, docs/README.md |
| テンプレート | sample_pack を利用 | sample_pack を社内文書向け最小構成として固定 | 拡張 | templates/sample_pack/README.md, templates/sample_pack/cases.csv, templates/sample_pack/quality-pack.yml |
| 実pack（見本） | 運用対象pack中心 | HR見本に加え Wiki/FAQ 見本を提供 | 新規（見本拡張） | packs/hr/README.md, packs/wiki/README.md |
| init-pack プロファイル | 既存プロファイル中心 | demo_cycle/sample/hr/wiki を選択可能に拡張 | 新規（機能拡張） | src/rqg/cli.py |
| Onboardingデモ | quickstartの基本導線 | profile 切替（demo_cycle/hr/wiki）対応 | 拡張 | src/rqg/demo/onboarding_quickstart.py, docs/demo/onboarding-quickstart.md |
| Onboarding workflow | スモーク実行 | workflow_dispatch で profile 選択可能 | 拡張 | .github/workflows/rqg-onboarding.yml |
| CI契約チェック | Phase2.5 の exit/risk control 検証 | internal-docs-pack-contract を追加し pack契約を検証 | 新規 | .github/workflows/ci.yml |
| quality-pack.yml の位置づけ | 任意活用（next action ヒント） | 縦パックの必須契約要素として固定 | 拡張 | src/rqg/quality/check.py, .github/workflows/ci.yml |

## 何が新規で、何が据え置きか（要点）

- 新規:
  - 社内文書向け縦パックの実装基準
  - HR/Wiki の見本パック
  - CI の internal-docs pack 契約チェック
  - init-pack / onboarding の profile 拡張
- 据え置き:
  - 品質ゲート基盤そのもの（ingest/eval/check/impact/review/CI の本体思想）
  - Phase2.5 で定義した週次運用コントロール（C1-C4, RC1-RC2）

## 移行観点（Phase2.5 から見ると）

- 既存運用（週次メトリクス、exit/risk 判定）は継続利用できる。
- 追加で必要なのは、pack 契約の明確化（quality-pack 含む）と profile 選択型オンボーディング。
- 破壊的変更よりも「導入導線と契約面の強化」が中心。
