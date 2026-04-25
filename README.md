# Proof Gate

[日本語](#日本語--japanese) | [English](#english)

## 日本語 / Japanese

Proof Gate は、RAG/Agent の品質を毎回同じやり方で検証し、高リスク更新の事故をリリース前に検知・遮断するための実運用向け品質ゲート基盤です。

この製品は AI を賢くするものではなく、AI を安全に更新・運用するための品質管理レイヤです。

最初の市場導線として、社内文書（規程・FAQ・手順書・ナレッジ記事・社内 Wiki）向け縦パックを同梱しています。
現在は HR プロファイルと Wiki/FAQ プロファイルの 2 つを見本として提供します。

## アーキテクチャ

```mermaid
flowchart LR
    subgraph Input
        D[documents/]
        C[cases.csv]
        Y[.rqg.yml]
    end
    subgraph "rqg gate （ワンコマンド）"
        I[ingest] -->|FAISS index| E[eval]
        C --> E
        E -->|JSONL logs| CH[check]
        Y --> CH
    end
    CH --> R[gate-report.md]
    CH --> J[gate-decision.json]
    J -->|exit 0/1| CI[CI / CD pipeline]

    style I fill:#e8f5e9
    style E fill:#e3f2fd
    style CH fill:#fff3e0
```

**データフロー**: documents → FAISS ingest → eval（キーワード + retrieval + reference 評価）→ check（閾値判定）→ pass/fail 出力

## この製品が解決すること

| 課題 | RQG の解決策 |
|------|-------------|
| 変更のたびに品質確認が属人化する | `rqg gate` で定型化。毎回同じ基準 |
| 重大ケースの取りこぼし | S1/S2 の severity 分離。S1 は 100% pass 必須 |
| fail 時にどこから直すべきか不明 | gate-report.md に failure category + next action |
| 判定自体の信頼性が見えない | judge / embedding fallback, reliability, needs_human_review を artifact に明示 |
| PR の品質判定が曖昧 | CI exit code 0/1 で機械的に判定 |

## なぜ RQG?（競合との位置づけ）

| | RQG | Ragas / DeepEval | LangSmith | Braintrust |
|---|---|---|---|---|
| **主目的** | 運用チーム向け回帰ゲート | LLM 評価フレームワーク | LLM observability | LLM eval + logging |
| **誰が使う** | QA・運用・ドメインオーナー | ML エンジニア | 開発者 | 開発者 |
| **CI gate** | ネイティブ対応 (exit 0/1) | 自分で組む | webhook/API | 自分で組む |
| **ケース資産管理** | cases.csv + merge/validate | なし | なし | Datasets |
| **severity 運用** | S1/S2 分離・閾値別 | なし | なし | なし |
| **API キー不要** | `--mock` で即体験 | 必要 | 必要 | 必要 |
| **導入コスト** | `pip install` + 1 コマンド | SDK 統合 | SaaS 登録 | SaaS 登録 |

**RQG は「評価の精度を極める」ツールではなく、「品質チェックを運用に定着させる」ためのゲート基盤です。**

## CLI コマンドマップ

```
rqg gate     ← 最初はこれだけ（eval + check のワンコマンド）
 ├── eval        回帰テスト実行
 ├── check       閾値判定 + レポート出力
 └── ingest      文書の FAISS インデックス作成

rqg validate-connection  外部RAG endpoint の接続/契約検証
rqg serve-http-rag      内蔵RAG を localhost の /search contract で公開
rqg validate-pack       pack 導入前の設定ミス検証
rqg history             gate decision の時系列比較と差分要約
rqg monthly-summary     月次の blocked run / fallback / unresolved issue 要約
rqg export-weekly-review  uncovered category から GitHub issue payload を生成
rqg gen-cases    ケース草案を文書から自動生成
rqg merge-cases  生成ケースを cases.csv に安全マージ
rqg validate-cases  cases.csv のバリデーション
rqg impact       文書変更の影響ケース特定

rqg init-pack    テンプレートから pack を初期化
rqg init-snapshot / create-sample-case / create-sample-gate  scaffold 用
rqg migrate-cases  レガシー参照の移行
rqg serve-dashboard     pack / run / monthly summary の閲覧UI
```

GitHub Actions 向けの導入テンプレートは `templates/github/` に同梱しています。
Reusable workflow は `templates/github/workflows/rqg-reusable-gate.yml`、caller 例は `templates/github/rqg-gate-*.yml` を使います。caller 側は `run_pack_validation` と `pack_validation_preset` を使うと、導入前 preflight を profile 別に揃えられます。
`rqg gate --dry-run` を使うと、isolated な `log_dir/dry-run/...` にだけ artifacts を書き、通知送信と gate history append を止めたまま gate 判定を確認できます。

**日常で使うのは `gate` (+ `gen-cases` / `merge-cases`) の 2-3 コマンドです。**

## 評価ツールとの違い

Ragas・DeepEval・LangSmith・Braintrust などの LLM 評価ツールは「スコアを出す」ところで完結します。
RQG は評価の先にある **運用サイクル全体** をカバーします。

| 能力 | 一般的な評価ツール | RQG |
|---|---|---|
| 回答品質スコアリング | ✅ | ✅ |
| 文書変更 → 影響ケース特定 (impact analysis) | — | ✅ |
| pass/warn/fail リリース判定 (release gate) | — | ✅ CI 統合済み |
| fail → 原因分類 → 改善アクション (next actions) | — | ✅ |
| 週次レビューと指標蓄積 (weekly review) | — | ✅ |
| severity 別運用 S1/S2 | — | ✅ |
| ドメイン縦パック (pack 運用) | — | ✅ |
| ケース自動追従 (migrate-cases) | — | ✅ |

一言で言えば、**eval で終わらず、gate → review → fix → re-eval のループを回す基盤** です。

## 縦パック（社内文書向けプロファイル）

このリポジトリでは、社内文書を知識源とする業務支援 AI 向けに次の 2 プロファイルを同梱しています。

- packs/hr: 人事・就業規程中心の HR プロファイル
- packs/wiki: 社内 FAQ/ナレッジベース中心の Wiki/FAQ プロファイル

- 文書更新時に impacted cases を特定する
- 重大ケース（S1）を優先して eval/check する
- pass/warn/fail で本番反映の可否を判断する
- fail を review と改善アクションに接続する

中身は水平な品質ゲート基盤のまま維持し、縦パックは導入しやすく価値を伝えるための入口として提供します。

## 使い方（3パターン）

### パターン A: ワンコマンド体験（30秒）

```bash
pip install -e .
rqg gate packs/hr/cases.csv --docs packs/hr/documents --mock --index-dir index --log-dir runs/quality --config .rqg.yml
cat runs/quality/gate-report.md
```

### パターン B: デモで全機能を体験（5-10分）

```bash
python -m rqg.demo.onboarding_quickstart
# Wiki/FAQ profile:
python -m rqg.demo.onboarding_quickstart --profile wiki
```

出力: `demo_runs/onboarding_quickstart/<run-id>/` 配下に summary.json, review.md, impact_review.md

### パターン D: 外部 RAG contract を 1 本通す（10分）

外部 endpoint 境界を先に固めたい場合は、`serve-http-rag -> validate-connection -> gate --dry-run -> gate -> notify -> history -> export-weekly-review` を 1 本で確認します。

- localhost quickstart: `docs/demo/external-contract-localhost.md`
- `gate-report.json` から weekly review payload までつなぐ downstream 例を含みます
- 最後に tunnel 越しで次段へ進む準備も載せています

### パターン C: 段階的に導入

```bash
# 1. テンプレート配置
rqg init-pack packs/my_pack

# 2. 導入前チェック
rqg validate-pack --pack-dir packs/my_pack

# 3. eval + check をワンコマンドで
rqg gate packs/my_pack/cases.csv \
  --docs packs/my_pack/documents \
  --mock --index-dir index --log-dir runs/quality \
  --config .rqg.yml

# 4. 出力を確認
cat runs/quality/gate-report.md
cat runs/quality/gate-decision.json
cat runs/quality/gate-report.json

# 5. ケースを育てる（任意）
rqg gen-cases --snapshot runs/snapshots/latest.json --output runs/casegen/cases.json --review-output runs/casegen/review.csv
rqg merge-cases --cases packs/my_pack/cases.csv --review runs/casegen/review.csv --in-place
```

Dry-run で本番用 history や通知を汚さずに gate 判定だけ見たい場合:

```bash
rqg gate packs/my_pack/cases.csv \
    --docs packs/my_pack/documents \
    --mock --index-dir index --log-dir runs/quality \
    --config packs/my_pack/gate.yml \
    --dry-run
```

`gate-report.json` は Markdown report、gate-decision.json、gate-history-summary.json を一つに束ねた machine-readable bundle です。GitHub 以外の downstream consumer はまずこの JSON を読むのが最短です。たとえば `rqg export-weekly-review --bundle-file runs/quality/gate-report.json` で weekly review issue payload を直接生成できます。

`gate-decision.json` には judge fallback、judge reliability、embedding fallback、needs_human_review、pack metadata も含まれます。Proof Gate の PoC では、この JSON を中心に意思決定と UI 表示を揃えます。

## ドキュメント案内

README は製品概要と導入に絞っています。技術仕様・運用設計の詳細は docs を参照してください。

- docs ポータル（日英）: docs/README.md

導入とデモ:

- docs/demo/onboarding-quickstart.md
- docs/demo/fail-fix-cycle.md
- docs/demo/impact-cycle.md
- docs/demo/external-contract-localhost.md
- packs/hr/README.md

技術設計:

- docs/adr/0001-model-boundaries.md
- docs/adr/0002-product-charter-and-development-priorities.md

運用設計（Phase2 / Phase2.5）:

- docs/ops/archive/phase2-migration-playbook.md
- docs/ops/archive/phase2-kickoff-board.md
- docs/ops/operations/phase2-weekly-metrics-register.md
- docs/ops/archive/phase2-5-hardening-plan.md
- docs/ops/operations/phase2-5-weekly-metrics-register.md
- docs/ops/operations/phase2-5-investigate-response-flow.md
- docs/ops/operations/phase2-5-case-quality-weekly-review.md
- docs/ops/operations/phase3-internal-docs-vertical-pack.md

## ライセンス

MIT

---

## English

RAG Quality Gate is a production-oriented quality-gate foundation that lets teams validate RAG/Agent quality in a repeatable way and connect results directly to release decisions.

This product does not make models smarter. It provides a quality-management layer for safe updates and operations.

As the first market-facing entry point, this repository includes internal-documents vertical packs (policy docs, FAQs, SOPs, knowledge pages, internal wiki style content).
There are two bundled profiles: HR and Wiki/FAQ.

## Architecture

```mermaid
flowchart LR
    subgraph Input
        D[documents/]
        C[cases.csv]
        Y[.rqg.yml]
    end
    subgraph "rqg gate (one command)"
        I[ingest] -->|FAISS index| E[eval]
        C --> E
        E -->|JSONL logs| CH[check]
        Y --> CH
    end
    CH --> R[gate-report.md]
    CH --> J[gate-decision.json]
    J -->|exit 0/1| CI[CI / CD pipeline]

    style I fill:#e8f5e9
    style E fill:#e3f2fd
    style CH fill:#fff3e0
```

**Data flow**: documents → FAISS ingest → eval (keyword + retrieval + reference scoring) → check (threshold decision) → pass/fail output

## Problems It Solves

| Problem | RQG Solution |
|---------|-------------|
| Quality checks become inconsistent | `rqg gate` standardizes them — same criteria every time |
| Critical cases are missed | S1/S2 severity separation; S1 requires 100% pass |
| Unclear what to fix on failure | gate-report.md shows failure category + next action |
| Ambiguous PR quality criteria | CI exit code 0/1 for machine-readable decisions |

## Why RQG? (Competitive Positioning)

| | RQG | Ragas / DeepEval | LangSmith | Braintrust |
|---|---|---|---|---|
| **Primary purpose** | Regression gate for ops teams | LLM evaluation framework | LLM observability | LLM eval + logging |
| **Target user** | QA, ops, domain owners | ML engineers | Developers | Developers |
| **CI gate** | Native (exit 0/1) | DIY | Webhook/API | DIY |
| **Case asset management** | cases.csv + merge/validate | None | None | Datasets |
| **Severity-based ops** | S1/S2 split with separate thresholds | None | None | None |
| **No API key needed** | `--mock` mode for instant demo | Required | Required | Required |
| **Setup cost** | `pip install` + 1 command | SDK integration | SaaS signup | SaaS signup |

**RQG is not about maximizing evaluation accuracy — it's about making quality checks stick in daily operations.**

## CLI Command Map

```
rqg gate     ← start here (eval + check in one command)
 ├── eval        run regression tests
 ├── check       threshold decision + report
 └── ingest      build FAISS index from documents

rqg gen-cases    auto-generate draft cases from documents
rqg merge-cases  safely merge generated cases into cases.csv
rqg validate-cases  validate cases.csv rows
rqg impact       identify impacted cases from document changes

rqg init-pack    scaffold a pack from bundled templates
rqg init-snapshot / create-sample-case / create-sample-gate  scaffolding
rqg migrate-cases  migrate legacy evidence references
rqg validate-connection  validate an external HTTP RAG endpoint
rqg serve-http-rag      expose the built-in RAG behind localhost /search
rqg export-weekly-review  export weekly review issue payload JSON
```

GitHub Actions templates live in `templates/github/`. Copy `templates/github/workflows/rqg-reusable-gate.yml` plus one caller example from `templates/github/rqg-gate-*.yml`. Use `pack_validation_preset` for common caller profiles (`local_docs`, `external`, `external_notify`).

**Day-to-day you only need `gate` (+ `gen-cases` / `merge-cases`) — 2-3 commands.**

## How RQG Differs From Eval Tools

Tools like Ragas, DeepEval, LangSmith, and Braintrust stop at scoring.
RQG covers the **full operational cycle** beyond evaluation.

| Capability | Typical eval tools | RQG |
|---|---|---|
| Answer quality scoring | ✅ | ✅ |
| Document change → impacted case detection (impact analysis) | — | ✅ |
| pass/warn/fail release decision (release gate) | — | ✅ CI-integrated |
| fail → root cause → corrective action (next actions) | — | ✅ |
| Weekly review and metrics accumulation (weekly review) | — | ✅ |
| Severity-based operations S1/S2 | — | ✅ |
| Domain vertical packs (pack operations) | — | ✅ |
| Automatic case migration (migrate-cases) | — | ✅ |

In short: **RQG does not stop at eval — it drives the gate → review → fix → re-eval loop.**

## Vertical Pack Profiles (Internal Documents)

This repository includes two internal-documents profiles for assistant AI.

- packs/hr: HR policy/procedure profile
- packs/wiki: internal FAQ/wiki operations profile

- Identify impacted cases when documents change
- Protect critical cases (S1) first during eval/check
- Decide production rollout with pass/warn/fail
- Connect failures to review and corrective actions

The product core remains horizontal. The vertical pack is an adoption and value-communication entry point.

## Usage (3 Patterns)

### Pattern A: One-Command Experience (30 seconds)

Bash:

```bash
pip install -e .
rqg gate packs/hr/cases.csv --docs packs/hr/documents --mock --index-dir index --log-dir runs/quality --config .rqg.yml
cat runs/quality/gate-report.md
```

PowerShell:

```powershell
pip install -e .
rqg gate packs\hr\cases.csv --docs packs\hr\documents --mock --index-dir index --log-dir runs\quality --config .rqg.yml
Get-Content runs\quality\gate-report.md -Encoding UTF8
```

### Install Profiles

Use the smallest install profile that matches the job:

```bash
# Client-facing demo, validate-pack/check/gate, and report viewing.
pip install -e .

# External RAG HTTP adapter and connection validation.
pip install -e ".[external]"

# Local embedding, FAISS index, and sentence-transformers features.
pip install -e ".[embedding]"

# Developer tools only: tests and formatting commands.
pip install -e ".[dev]"

# Full local test setup, including external, serve, and embedding extras.
pip install -e ".[all]"
```

Full test runs that exercise local FAISS-backed retrieval should use `pip install -e ".[all]"`. The lightweight client demo does not require `sentence-transformers`.

### Pattern B: Full Demo (5-10 minutes)

Bash / PowerShell:

```bash
python -m rqg.demo.onboarding_quickstart
# Wiki/FAQ profile:
python -m rqg.demo.onboarding_quickstart --profile wiki
```

Outputs: `demo_runs/onboarding_quickstart/<run-id>/` with summary.json, review.md, impact_review.md

### Pattern D: External RAG contract proof (10 minutes)

If you want to prove the external endpoint boundary first, use the `serve-http-rag -> validate-connection -> gate --dry-run -> gate -> notify -> history -> export-weekly-review` story.

- localhost quickstart: `docs/demo/external-contract-localhost.md`
- includes one downstream example from `gate-report.json` to weekly review payload
- ends with tunnel-ready prep for the next external-like hop

### Pattern C: Gradual Adoption

Bash:

```bash
# 1. Scaffold a pack
rqg init-pack packs/my_pack

# 2. Run eval + check in one command
rqg gate packs/my_pack/cases.csv \
  --docs packs/my_pack/documents \
  --mock --index-dir index --log-dir runs/quality \
  --config .rqg.yml

# 3. Review outputs
cat runs/quality/gate-report.md
cat runs/quality/gate-decision.json

# 4. Grow your cases (optional)
rqg gen-cases --snapshot runs/snapshots/latest.json --output runs/casegen/cases.json --review-output runs/casegen/review.csv
rqg merge-cases --cases packs/my_pack/cases.csv --review runs/casegen/review.csv --in-place
```

PowerShell:

```powershell
# Optional: keep Markdown and report output readable in Windows PowerShell.
chcp 65001
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 1. Scaffold a pack
rqg init-pack packs\my_pack

# 2. Validate pack onboarding inputs
rqg validate-pack --pack-dir packs\my_pack

# 3. Run eval + check in one command
rqg gate packs\my_pack\cases.csv `
  --docs packs\my_pack\documents `
  --mock --index-dir index --log-dir runs\quality `
  --config .rqg.yml

# 4. Review outputs
Get-Content runs\quality\gate-report.md -Encoding UTF8
python -m json.tool runs\quality\gate-decision.json
python -m json.tool runs\quality\gate-report.json

# 5. Grow your cases (optional)
rqg gen-cases --snapshot runs\snapshots\latest.json --output runs\casegen\cases.json --review-output runs\casegen\review.csv
rqg merge-cases --cases packs\my_pack\cases.csv --review runs\casegen\review.csv --in-place
```

For virtual environment setup, environment variables, UTF-8 console notes, and more PowerShell examples, see [Windows PowerShell command guide](docs/user-guide/windows-powershell.md).

If Markdown output looks garbled on Windows PowerShell, run the UTF-8 setup commands above or open the file in VS Code.

## Documentation

This README focuses on product overview and onboarding. See docs for detailed technical and operational guidance.

- docs portal (JP/EN): docs/README.md

Getting started and demos:

- docs/user-guide/windows-powershell.md
- docs/demo/vendor-poc-walkthrough.md
- docs/demo/onboarding-quickstart.md
- docs/demo/fail-fix-cycle.md
- docs/demo/impact-cycle.md
- docs/demo/external-contract-localhost.md
- packs/hr/README.md

Architecture:

- docs/adr/0001-model-boundaries.md
- docs/adr/0002-product-charter-and-development-priorities.md

Operations (Phase2 / Phase2.5):

- docs/ops/archive/phase2-migration-playbook.md
- docs/ops/archive/phase2-kickoff-board.md
- docs/ops/operations/phase2-weekly-metrics-register.md
- docs/ops/archive/phase2-5-hardening-plan.md
- docs/ops/operations/phase2-5-weekly-metrics-register.md
- docs/ops/operations/phase2-5-investigate-response-flow.md
- docs/ops/operations/phase2-5-case-quality-weekly-review.md
- docs/ops/operations/phase3-internal-docs-vertical-pack.md

## License

MIT
