# RAG Quality Gate

RAG/Agent システム向けに、回帰検証とリリース判定を継続運用するための品質ゲート基盤です。

このリポジトリでは、以下をエンドツーエンドで実行できます。

- 文書を ingest して DocumentSnapshot を生成
- テストケースを EvalCase として管理
- eval 実行で回答品質を評価
- check 実行で GateDecision を生成
- gen-cases で初期ケースを自動生成
- impact で文書更新時の影響ケースを抽出
- CI で PR の pass/fail を自動判定

## 5-10分クイックスタート（初回導入者向け）

最短で 1 回導入体験する場合は、次の 1 コマンドを実行してください。

```bash
python -m rqg.demo.onboarding_quickstart
```

このデモは次の流れを 1 回通します。

1. ingest
2. gen-cases
3. eval
4. check
5. impact
6. review 出力

出力は `demo_runs/onboarding_quickstart/<run-id>/` に保存されます。

主な成果物:

- artifacts/eval_cases.json
- artifacts/eval_cases_review.md
- artifacts/impact_report.json
- artifacts/impact_review.md
- summary.json

詳細は docs/demo/onboarding-quickstart.md を参照してください。

## このプロジェクトの目的

RAG は文書更新、検索条件変更、プロンプト調整で品質が変化しやすく、変更の影響が見えにくい課題があります。

本プロジェクトは次を実現します。

- 変更前後の品質を再現可能に比較する
- 重大ケースを優先して守る
- 問題発生時に、どのケースを見直すべきかを明確にする
- リリース判定を運用可能な形で自動化する

## 最小セットアップ

要件:

- Python 3.11+
- pip

インストール:

```bash
pip install -e ".[dev]"
```

CLI ヘルプ:

```bash
rqg --help
```

## 3ステップ導入（テンプレート標準）

初回導入を最短化するために、以下のテンプレートを用意しています。

- templates/policy.yaml
- templates/github/workflows/rqg-onboarding.yml
- templates/sample_pack/

Step 1. テンプレートを配置

```bash
cp templates/policy.yaml .rqg.yml
mkdir -p .github/workflows
cp templates/github/workflows/rqg-onboarding.yml .github/workflows/
cp -r templates/sample_pack packs/my_pack
```

Step 2. サンプル pack で実行

```bash
rqg ingest packs/my_pack/documents --index-dir index
rqg eval packs/my_pack/cases.csv --docs packs/my_pack/documents --mock --index-dir index --log-dir runs/quality
rqg check --log-dir runs/quality --config .rqg.yml
```

Step 3. 成果物を確認

- runs/quality/gate-report.md
- runs/quality/gate-decision.json
- templates/sample_pack/reports/example-impact-report.json

PRごとの導入スモークは、workflow_dispatch または pull_request で
`rqg-onboarding.yml` が実行します。

## 最小実行フロー

同梱の HR pack を使って最小構成を実行できます。

```bash
# 1) 文書を投入して snapshot を生成
rqg ingest packs/hr/documents/ --index-dir index

# 2) 評価を実行
rqg eval packs/hr/cases.csv --docs packs/hr/documents/ --mock --index-dir index --log-dir runs/quality

# 3) ゲート判定を実行して GateDecision を出力
rqg check --log-dir runs/quality --config .rqg.yml --output-file runs/quality/gate-report.md --decision-file runs/quality/gate-decision.json
```

主な成果物:

- index/snapshots/*.json: DocumentSnapshot
- runs/quality/*.jsonl: eval 実行ログ
- runs/quality/gate-report.md: ゲートレポート
- runs/quality/gate-decision.json: GateDecision

## 初期ケース自動生成

DocumentSnapshot からレビュー可能な EvalCase 候補を生成できます。

```bash
# 1) snapshot JSON を作成
rqg init-snapshot \
  --snapshot-id snapshot_001 \
  --doc-id hr_rules \
  --title "HR Rules" \
  --source-path packs/demo_cycle/documents/leave_policy.md \
  --content "Paid leave requests must be submitted 5 business days in advance." \
  --output artifacts/doc_snapshot.json

# 2) ケース候補を生成 (JSON + 任意でレビュー用 Markdown)
qgate gen-cases \
  --snapshot artifacts/doc_snapshot.json \
  --output artifacts/eval_cases.json \
  --review-output artifacts/eval_cases_review.md \
  --mode rule
```

- JSON 出力は常に生成されます
- review-output 指定時のみレビュー用 Markdown を生成します

## Impact Analysis (Phase 1.5)

文書更新時に、どのケースを優先見直しすべきかを抽出します。

目的:

- old/new snapshot を比較
- changed_evidence_ids を抽出
- expected_evidence を使って impacted_case_ids を特定

```bash
qgate impact \
  --old-snapshot artifacts/old_snapshot.json \
  --new-snapshot artifacts/new_snapshot.json \
  --cases artifacts/eval_cases.json \
  --output artifacts/impact_report.json \
  --review-output artifacts/impact_report_review.md
```

入力:

- --old-snapshot: 変更前 DocumentSnapshot JSON
- --new-snapshot: 変更後 DocumentSnapshot JSON
- --cases: EvalCase JSON または CSV

出力:

- impact_report.json (ImpactReport)
  - old_snapshot_id
  - new_snapshot_id
  - changed_evidence_ids
  - impacted_case_ids
  - details (case_id, matched_evidence_id, question, match_mode)
  - created_at
- review-output 指定時のみレビュー用 Markdown

CLI 標準出力には以下のサマリも表示されます。

- Changed evidence count
- Impacted case count

運用メモ (Phase 1.5 仕上げ):

- section_id は doc_id ベースで生成されます（パス変更に強くするため）
- 新規ケース作成時は doc_id を安定した論理IDとして運用してください

移行完了条件:

- source_path ベース expected_evidence を doc_id ベースへ移行完了
- unresolved_legacy_refs 0 件を継続確認

### expected_evidence 移行補助ツール

legacy な source_path ベース `expected_evidence` を `doc_id#...` 形式へ変換できます。

```bash
rqg migrate-cases \
  --cases artifacts/eval_cases.json \
  --snapshot artifacts/old_snapshot.json \
  --snapshot-dir index/snapshots \
  --output artifacts/eval_cases_migrated.json \
  --report artifacts/migration_report.json
```

- `--snapshot` は複数指定できます
- `--snapshot-dir` 配下の snapshot JSON も変換マップに利用されます
- `--report` には変換件数・未解決件数が保存されます

### 文書更新時の推奨運用フロー

1. 現行文書を ingest して snapshot を保存
2. ケースを生成または更新
3. 文書を更新
4. 更新後文書を ingest して snapshot を保存
5. qgate impact を実行
6. unresolved_legacy_refs を確認し、必要なら rqg migrate-cases でケース移行
7. impacted cases を優先レビュー
8. rqg eval と rqg check を実行
9. 必要な修正後に pass を確認

## デモ

### fail -> fix -> pass デモ

```bash
python -m rqg.demo.fail_fix_cycle
```

### impact を含む通しデモ

```bash
python -m rqg.demo.impact_cycle
```

関連ドキュメント:

- docs/demo/onboarding-quickstart.md
- docs/demo/fail-fix-cycle.md
- docs/demo/impact-cycle.md
- docs/adr/0001-model-boundaries.md
- docs/ops/phase2-migration-playbook.md

## Phase2 開始前チェック

Phase2（旧形式の計画的削減）へ進む前に、以下を固定してください。

1. 対象ケース母集団の確定（owner/期限を明記）
2. impacted_case_count と unresolved_legacy_refs の週次計測
3. migrate-cases 実行手順とロールバック条件の合意
4. 期限後撤去タスクの担当・実行タイミング確定

詳細は docs/ops/phase2-migration-playbook.md を参照してください。

運用開始後の固定情報と週次メトリクスは以下を参照してください。

- docs/ops/phase2-kickoff-board.md
- .github/workflows/phase2-weekly-metrics.yml
- docs/ops/phase2-weekly-metrics-register.md
- .github/PULL_REQUEST_TEMPLATE/issue4-post-expiry-cleanup.md

## Phase2.5 開始

Phase2.5（実運用で壊れにくくする）へ移行する場合は、以下の計画書を起点に進めてください。

- docs/ops/phase2-5-hardening-plan.md
- docs/ops/phase2-5-ws1-baseline-sheet.md

WS1 の時間 target（初回導入 30分以内 / 週次運用 15分以内）は、以下の測定条件を固定した値として扱います。

- 対象は sample repo への導入（例: packs/hr ベース）
- 既存顧客 repo への組み込みは別トラックで測定（target 判定対象外）
- 初回ケース設計・ケース追加の時間は除外（導入/運用フローのみ計測）

## Phase 1 / 1.5 実装状況

- [x] ingest 時に DocumentSnapshot を自動生成
- [x] CSV ケースを EvalCase に正規化
- [x] rqg eval 実行
- [x] rqg check で GateDecision 生成
- [x] gen-cases でケース自動生成
- [x] impact で影響ケース抽出
- [x] レビュー用 Markdown 出力
- [x] CI で PR pass/fail 判定

## プロジェクト構成

```text
src/rqg/
  serving/        # RAG パイプライン (FAISS + sentence-transformers + OpenAI)
  quality/        # 品質評価・集計・ゲート判定・impact 分析
  casegen/        # セクション抽出・質問生成・ケース生成
  domain/         # DocumentSnapshot / EvalCase / GateDecision / ImpactReport
  presentation/   # レビュー向け Markdown フォーマッタ
  demo/           # 再現可能なデモシナリオ
  cli.py          # CLI エントリポイント
packs/            # ドメイン別 Quality Pack
templates/        # 導入テンプレート (policy/workflow/sample pack)
tests/            # pytest
```

## Quality Pack

ドメインごとに次のファイルを持ちます。

- cases.csv: テストケース
- quality-pack.yml: KPI/SLO 定義
- documents/: 対象文書

CSV 例:

```csv
case_id,name,severity,question,expected_chunks,expected_keywords,golden_answer,category,owner,min_pass_rate
QA001,有給申請期限,S1,"有給の申請期限は？","","5営業日前;申請","",就業規則,hr-team,100
```

## Gate Config (.rqg.yml)

```yaml
thresholds:
  s1_pass_rate: 100.0
  overall_pass_rate: 80.0
  retrieval_precision: 70.0
```

## 評価軸

- keyword_match: 回答に期待キーワードが含まれるか
- retrieval_hit: 正しいチャンクが検索に含まれるか
- reference_accuracy: 回答中の引用整合性

## CI 連携

```yaml
- name: RAG Quality Gate
  run: |
    rqg eval packs/hr/cases.csv --docs packs/hr/documents/ --mock
    rqg check --log-dir runs/quality --config .rqg.yml
```

## 開発コマンド

```bash
# テスト
pytest tests/ -v

# フォーマット
black src/ tests/
isort src/ tests/

# カバレッジ
pytest tests/ --cov=rqg --cov-report=term-missing
```

## ライセンス

MIT
