# Gate Review Architecture Gap Analysis

## 1. Purpose

このドキュメントは、現在の Proof Gate 実装・docs・templates が、`gate_history` を機械可読な正本、`Gate Review` を人間向け判断レイヤー、`Investigation` / `Action Item` を補助記録として分離する設計思想にどこまで一致しているかを整理するための差分分析です。

目的は即時の大規模実装変更ではなく、現状のズレを明確にし、次に直すべき優先事項を設計レベルで固定することです。

## 2. Target Architecture

理想形は、機械可読な実行履歴と、人間の判断・原因調査・対応管理を明確に分離することです。

```text
gate_history (machine-readable source of truth)
  - gate-decision.json
  - gate-report.json
  - gate-history-summary.json
  - gate-decisions.jsonl
  - artifact refs / run metadata
        ↓
Gate Review (human decision layer)
  - customer-facing primary review document
  - PASS / BLOCK / REVIEW / CONDITIONAL
  - links back to gate_history
        ↓
Investigation (only when needed)
  - root cause analysis for BLOCK / REVIEW / CONDITIONAL
        ↓
Action Item
  - execution task tracking tied to review/investigation
```

```text
gate_history = machine-readable source of truth
reviews/ = human decision and response layer
```

## 3. Current Implementation Summary

### `weekly_review.py`

- `src/rqg/quality/weekly_review.py` は `gate-history-summary.json` を元に GitHub Issue payload を生成する。
- 出力概念は `Gate Review` ではなく `Weekly Review issue` で、title prefix も既定で `[Phase2.5][Weekly Review]`。
- payload は本文中心で、`review_id` / `gate_history_ref` / `decision` などの構造化 review metadata を持たない。

### `export-weekly-review`

- `src/rqg/cli/export_weekly_review.py` は `gate-history-summary.json` または `gate-report.json` の `history_summary` を読み、`weekly-review-issue.json` を出力する。
- CLI 名称も export 先も `weekly review issue` 前提で、Gate Review 生成器ではない。

### gate history generation

- `src/rqg/cli/check.py` が `gate-report.md` / `gate-report.json` / `gate-decision.json` / `gate-history-summary.json` / `gate-decisions.jsonl` を生成する。
- `src/rqg/quality/history.py` が recent history summary, comparison, coverage, stale case review, reliability を構造化して `gate-history-summary.json` に出す。
- `src/rqg/quality/reporting.py` の bundle は `artifact_paths` を持ち、`gate-report.json` に `decision`, `history_summary`, `report_markdown` をまとめる。

### phase2-5 workflows

- `.github/workflows/phase2-5-weekly-review-issue.yml` と `.github/workflows/phase2-5-weekly-metrics.yml` は内部運用の weekly issue フローを持つ。
- 命名、labels、本文、関連 docs が `Phase2.5` / `weekly review` / `ops` に強く寄っている。

### `templates/github/rqg-gate-weekly-review.yml`

- 顧客向けテンプレートでも downstream automation は `weekly review issue` を upsert する設計。
- optional な GitHub Project / Slack 連携はあるが、顧客向け主資料が Gate Review であるという概念整理はない。

### customer template

- `templates/customer-rqg-template/` は `cases.csv`, `documents/`, `adapter/`, `reports/` などを持つが、`reviews/` は存在しない。
- README は `gate-report.md` を人間確認の中心資料として案内している。

### tests

- `tests/test_weekly_review_export.py` は current contract を `weekly review issue` として固定している。
- `tests/test_github_templates.py` は `[Phase2.5][Weekly Review]` や `phase2-5` labels を repo/workflow contract として確認している。

## 4. Gap Analysis

| Area | Current State | Target State | Gap | Priority |
|---|---|---|---|---|
| Naming | `Weekly Review`, `Phase2.5`, `issue` が前面に出る | 顧客向けは `Gate Review`、内部運用は別名で分離 | 顧客向け概念と内部運用名が混在 | P0 |
| Gate History relation | history artifacts は生成済み、bundle に artifact refs あり | `gate_history` を source of truth として明示し、review から参照する | review 側の link metadata と概念説明が不足 | P0 |
| Gate Review concept | 独立概念として未実装。weekly issue が代替 | 人間向け主判断資料として独立 | 判断レイヤーが issue 本文に埋没 | P0 |
| Customer review burden | README は report 中心、raw artifacts / weekly review / internal docs の境界が曖昧 | 顧客向け主資料を Gate Review に集約 | 顧客が何を見ればよいか一意でない | P0 |
| file-based `reviews/` | customer template に存在しない | 初期 PoC は file-based `reviews/` を標準化 | 軽量運用の受け皿がない | P0 |
| GitHub Issues automation | weekly issue automation は Phase2.5/internal naming 前提 | 顧客向け generic workflow を optional 提供 | 顧客 repo にそのまま出しづらい | P1 |
| Metadata for LLM search | history summary は一部構造化済み | review / investigation / action item まで id/link/status を構造化 | 検索・監査・追跡用 metadata が不足 | P1 |
| Customer template | reports はあるが reviews layer 不在 | gate_history と reviews layer を併記 | 判断レイヤーの置き場所がない | P0 |
| Docs | internal ops docs は豊富、顧客向け review architecture 説明は不足 | artifacts の役割差分を docs で固定 | internal terminology が顧客向け導線に漏れる | P0 |

## 5. Recommended Design

- `gate_history` は引き続き source of truth とする。`gate-decision.json`, `gate-report.json`, `gate-history-summary.json`, `gate-decisions.jsonl` は置き換えない。
- `Gate Review` は顧客向け主判断資料にする。顧客が本番反映可否を判断する主資料はここに集約する。
- `Gate Report` は Gate Review の詳細根拠資料として扱い、通常の顧客判断資料を raw artifacts に拡散しない。
- `Investigation` と `Action Item` は補助記録に限定し、問題時だけ作成する。
- 初期 PoC では GitHub Issues を必須にせず、`reviews/` ディレクトリで file-based に運用する。
- 継続運用や成熟顧客向けには、GitHub Issues / Project Board / Slack 通知を optional extension として提供する。
- 既存の `Phase2.5` workflow は内部運用として残す。ただし顧客向け docs / templates / naming には露出させない。
- 顧客向け workflow は `Phase2.5` ではなく `ProofGate` / `Gate Review` の命名で分離する。

## 6. Proposed Directory Structure

`templates/customer-rqg-template/` 向けの推奨構成:

```text
reviews/
  README.md
  gate_reviews/
    .gitkeep
  investigations/
    .gitkeep
  action_items/
    .gitkeep
  templates/
    gate_review.md
    investigation.md
    action_item.md
```

補足:

- `reports/` は gate_history 関連の出力保管先として残してよい。
- `reviews/` は顧客判断・調査・対応の human layer として新設する。
- `logs/` や `runs/` は実行 artifacts であり、顧客向け primary review location にしない。

## 7. Proposed Metadata Schema

### Gate Review Metadata

- `review_id`
- `client_id`
- `gate_run_id`
- `gate_history_ref`
- `decision`
- `risk_areas`
- `severity`
- `pack_version`
- `gate_policy_version`
- `source_report`
- `status`

### Investigation Metadata

- `investigation_id`
- `client_id`
- `linked_gate_review`
- `gate_run_id`
- `gate_history_ref`
- `failure_category`
- `root_cause_type`
- `severity`
- `status`
- `owner`

### Action Item Metadata

- `action_id`
- `client_id`
- `linked_gate_review`
- `linked_investigation`
- `gate_run_id`
- `gate_history_ref`
- `risk_area`
- `status`
- `owner`
- `due_date`

## 8. Implementation Plan

### P0

- docs で `gate_history` / `Gate Review` / `Investigation` / `Action Item` の概念を固定する
- customer template に `reviews/` を追加する
- customer template README に Gate Review と他 artifact の違いを明記する
- 顧客向け主資料を Gate Review に集約する導線を追加する

### P1

- 顧客向け GitHub Issues workflow を `Phase2.5` から分離する
- title prefix を `[ProofGate][Gate Review]` にする
- labels を `proofgate`, `gate-review`, `ops` にする
- GitHub Projects / Slack 通知を optional extension として明記する

### P2

- Gate Review payload exporter を追加する
- `gate_history` から Gate Review draft を生成できるようにする
- review / investigation / action item の metadata index を検討する
- LLM 検索向けに review layer の structured export を検討する

## 9. Risks and Non-goals

- 既存 `Phase2.5` workflow を壊さない。内部運用フローは互換維持する。
- 今回は顧客横断 LLM 検索を実装しない。
- 顧客固有情報や secret を共通 repo に入れない。
- review 資料を増やすこと自体を目的にしない。判断資料は Gate Review に集約する。
- `gate-report.json` / `GateDecision` / `QARunRecord` / `cases.csv` など既存契約は migration plan なしに壊さない。

## 10. TODO Issues

- Add customer template `reviews/` directory
- Add `reviews/README.md` and review/investigation/action item markdown templates
- Add customer-facing Gate Review architecture doc to template README
- Add customer weekly review workflow without `Phase2.5` naming
- Add Gate Review metadata fields and sample frontmatter
- Add Gate Review exporter that links to `gate_history`
- Align `gate_history` artifact paths with review metadata references
- Add tests for `reviews/` template presence
- Add docs that distinguish Gate Review / Gate Report / Investigation / Action Item / raw artifacts
- Add anonymization guidance for reusable failure-pattern knowledge

## Current State by Review Lens

### A. Naming・概念の差分

**現状**

- 実装・CLI・workflow・tests が `Weekly Review` を主語にしている。
- `Gate Review` という独立概念は未定義。
- `Phase2.5`, `hardening`, `weekly review`, `issue` が顧客向け template/README に露出している。

**問題点**

- 顧客向け用語と内部運用用語が混ざる。
- review 記録と GitHub Issue 実装手段が同一視される。
- file-based 運用に切り替える概念上の余地が小さい。

**修正案**

- 顧客向け総称を `Gate Review` に統一する。
- `Weekly Review` は cadence 名、`Issue` は optional transport として格下げする。
- `Phase2.5` は internal-only naming に閉じ込める。

### B. gate_historyとの関係

**現状**

- `gate_history` 系 artifact は生成されており、bundle も存在する。
- `gate-history-summary.json` は比較・coverage・stale/reliability を構造化済み。
- ただし review 側 payload は `gate_run_id`, `gate_history_ref`, `source_report` を保持しない。

**足りない metadata**

- `review_id`
- `gate_run_id`
- `gate_history_ref`
- `source_report`
- `pack_version`
- `gate_policy_version`
- review decision/status

**改善案**

- review layer は常に `gate_history` を参照する metadata を持つ。
- `gate_history` と review を相互参照できるようにする。
- review を source of truth にせず、判断メモとして明示する。

### C. 顧客向け判断負荷

**現状**

- customer README は `gate-report.md` と `gate-report.json` を中心に案内している。
- weekly review issue, internal ops docs, raw artifacts との違いは顧客向けに整理されていない。

**顧客が迷う点**

- 何が主判断資料か不明確。
- `gate-report.md` と review/ticket の役割分担が不明。
- raw artifacts をどこまで見ればよいか判断しづらい。

**改善案**

- 顧客向け README に「まず Gate Review、必要時のみ Gate Report / artifacts」を明記する。
- Gate Review / Gate Report / Investigation / Action Item / raw artifacts の違いを表で固定する。

### D. file-based `reviews/` 運用

**現状**

- `templates/customer-rqg-template/reviews/` は存在しない。
- gate review / investigation / action item テンプレートもない。

**追加すべきファイル**

- `reviews/README.md`
- `reviews/gate_reviews/.gitkeep`
- `reviews/investigations/.gitkeep`
- `reviews/action_items/.gitkeep`
- `reviews/templates/gate_review.md`
- `reviews/templates/investigation.md`
- `reviews/templates/action_item.md`

**推奨ディレクトリ構成**

- Section 6 の構成を customer template に追加する。

### E. GitHub Issues自動化との関係

**現状**

- Issue 自動化は `Phase2.5` internal ops 用に最適化されている。
- title prefix と labels が固定で internal naming に依存する。
- GitHub Projects / Slack は optional だが、顧客 workflow でも internal convention が前提。

**顧客向けにそのまま使いづらい点**

- 顧客 repo に `Phase2.5` を露出させる。
- `Weekly Review issue` が唯一の review record に見える。
- 顧客向け metadata schema がない。

**汎用化案**

- internal workflow は現状維持。
- 追加で customer-facing workflow を分離し、`[ProofGate][Gate Review]` prefix と generic labels を採用する。
- GitHub Projects / Slack は optional example として残す。

### F. LLM検索・ナレッジ化への準備

**現状**

- `gate_history` 側は比較的構造化されている。
- review / investigation / action item layer は未整備。
- docs/agents には「顧客固有情報を混ぜない」方針がある。

**LLM検索に足りない構造**

- review/investigation/action item の stable ID
- link fields
- status / owner / due date
- risk area / severity
- client-scoped reference design

**追加すべき metadata**

- `client_id`
- `review_id`
- `investigation_id`
- `action_id`
- `gate_run_id`
- `gate_history_ref`
- `risk_area`
- `status`
- `owner`
- `due_date`

また、顧客横断検索は原則避け、共通資産化する場合は failure pattern を匿名化・抽象化して docs に明記するのが望ましい。
